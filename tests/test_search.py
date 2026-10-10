import pytest

from quizforge import retrieve
from quizforge.config import load_config
from quizforge.search import search_library, section_of, tool

CFG = load_config()


@pytest.mark.parametrize(
    "query, lesson",
    [
        ("start with the smallest tier that can clearly do the job", "L1.3"),
        ("what to check first when an answer might be a hallucination", "L3.2"),
        ("when is a chain of prompts better than one prompt", "L2.2"),
    ],
)
def test_a_known_query_finds_its_lesson_first(query, lesson):
    assert search_library(CFG.library, query)[0]["source"].startswith(lesson + "#")


def test_results_are_well_formed_search_result_blocks_with_citations():
    found = search_library(CFG.library, "model tier latency cost")
    assert 1 <= len(found) <= 3
    for block in found:
        assert block["type"] == "search_result" and block["citations"] == {"enabled": True}
        assert "#" in block["source"] and block["title"].lower().replace(" ", "-").endswith(
            block["source"].split("#")[1]
        )
        assert [part["type"] for part in block["content"]] == ["text"] and block["content"][0]["text"].strip()


def test_lesson_id_keeps_the_search_inside_one_lesson():
    found = search_library(CFG.library, "prompt", lesson_id="L1.3")
    assert found and all(block["source"].startswith("L1.3#") for block in found)


def test_sections_are_heading_level_chunks_without_chapters_or_sources():
    sources = [c["source"] for c in retrieve.chunks(CFG.library)]
    assert len(sources) == len(set(sources))
    assert not any(s.endswith(("#chapters", "#sources")) for s in sources)


def test_a_bad_query_or_lesson_is_an_instructive_error():
    with pytest.raises(ValueError, match="key words"):
        search_library(CFG.library, "  ")
    with pytest.raises(ValueError, match="ids look like L1.3"):
        search_library(CFG.library, "tier", lesson_id="1.3")


def test_a_saved_quote_keeps_the_section_it_came_from():
    block = search_library(CFG.library, "smallest tier", lesson_id="L1.3")[0]
    sentence = next(s for s in block["content"][0]["text"].split(". ") if len(s.split()) > 6)
    assert section_of(CFG.library, "L1.3", sentence) == block["source"]


def test_the_tool_is_described_and_needs_only_a_query():
    t = tool(CFG.library)
    assert t["name"] == "search_library" and len(t["description"].split(". ")) >= 3
    assert t["input_schema"]["required"] == ["query"] and "L1.3" in t["input_schema"]["properties"]["lesson_id"]["enum"]
