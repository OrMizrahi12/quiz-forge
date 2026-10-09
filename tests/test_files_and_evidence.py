from types import SimpleNamespace

import anthropic
import pytest

from quizforge import evidence, files
from quizforge.config import load_config

CFG = load_config()
QUESTION = {"scenario": "What should they check first?", "a": "The logs", "b": "The docs", "c": "The tests",
            "d": "The budget", "answer": "C", "why": "", "quote": ""}


class FilesFake:
    def __init__(self, gone=()):
        self.uploads, self.gone, self.requests = 0, set(gone), []
        self.files, self.messages = self, self

    def upload(self, file):
        self.uploads += 1
        return SimpleNamespace(id=f"file_{self.uploads}")

    def retrieve_metadata(self, fid):
        if fid in self.gone:
            gone = anthropic.NotFoundError.__new__(anthropic.NotFoundError)   # the SDK's 404, without an HTTP response
            Exception.__init__(gone, "file not found")
            raise gone
        return SimpleNamespace(id=fid)

    def create(self, **request):
        self.requests.append(request)
        cite = SimpleNamespace(type="page_location", cited_text="Tests show the feature works. ", start_page_number=2)
        content = [SimpleNamespace(type="text", text="Question 1: ", citations=None),
                   SimpleNamespace(type="text", text="the tests come first", citations=[cite])]
        return SimpleNamespace(content=content, usage=SimpleNamespace(input_tokens=9000, output_tokens=80))


@pytest.fixture
def index(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "INDEX", tmp_path / "files.json")


def test_a_file_is_uploaded_once_then_reused_by_its_file_id(tmp_path, index):
    pdf = tmp_path / "L1.3.pdf"
    pdf.write_bytes(b"%PDF-1.4 a small test file")
    client = FilesFake()
    assert files.file_id(client, pdf) == ("file_1", True)
    assert files.file_id(client, pdf) == ("file_1", False)
    assert client.uploads == 1


def test_a_deleted_file_is_uploaded_again(tmp_path, index):
    pdf = tmp_path / "L1.3.pdf"
    pdf.write_bytes(b"%PDF-1.4 a small test file")
    files.file_id(FilesFake(), pdf)
    client = FilesFake(gone={"file_1"})
    assert files.file_id(client, pdf) == ("file_1", True) and client.uploads == 1


def test_evidence_sends_the_file_id_with_citations_on_and_reads_the_pages(index):
    client = FilesFake()
    claims, used, uploaded = evidence.evidence(client, CFG, "L1.3", [QUESTION])
    (document, ask) = client.requests[0]["messages"][0]["content"]
    assert document["source"] == {"type": "file", "file_id": "file_1"} and document["citations"] == {"enabled": True}
    assert "output_config" not in client.requests[0]   # citations and structured outputs can't be combined
    assert "Correct: C) The tests" in ask["text"]
    assert claims[-1]["citations"] == [("Tests show the feature works.", 2)] and uploaded


def test_a_lesson_without_a_pdf_is_a_clear_error():
    with pytest.raises(FileNotFoundError, match="no PDF for L9.9"):
        evidence.pdf_of(CFG, "L9.9")
