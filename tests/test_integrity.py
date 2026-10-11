import json

from quizforge.security import integrity


def approved(tmp_path):
    (tmp_path / "L1.3.json").write_text(json.dumps({"lesson": "L1.3", "questions": [{"answer": "B"}]}))
    integrity.seal(tmp_path)
    return tmp_path


def test_a_sealed_bank_verifies(tmp_path):
    assert integrity.verify(approved(tmp_path)) == []


def test_a_change_after_approval_is_found(tmp_path):
    folder = approved(tmp_path)
    (folder / "L1.3.json").write_text(json.dumps({"lesson": "L1.3", "questions": [{"answer": "A"}]}))
    assert integrity.verify(folder) == ["changed after approval: L1.3.json"]


def test_a_file_added_without_approval_and_a_missing_one_are_found(tmp_path):
    folder = approved(tmp_path)
    (folder / "L1.3.json").rename(folder / "L2.1.json")
    assert integrity.verify(folder) == ["not approved: L2.1.json", "missing: L1.3.json"]
