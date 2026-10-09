"""The writer's library search: lesson sections scored with retrieve.py's BM25, sent back as search results Claude can cite.
The agent looks up what it needs, when it needs it, instead of carrying whole lessons in its context."""
from quizforge import retrieve
from quizforge.library import lesson_ids
from quizforge.sanitize import clean
from quizforge.validate import words

K = 3   # sections per search: enough to choose from, few enough to keep the context small


def tool(library):
    return {"name": "search_library",
            "description": "Searches the lesson notes of the Quiz Forge library and returns the three sections that best "
                           "match the query (a keyword score), as search results you can cite. Give lesson_id to search "
                           "one lesson only. Use a few key words, not a sentence; search again with other words if the "
                           "results don't cover what you need. It searches only the library: nothing on the web.",
            "input_schema": {"type": "object",
                             "properties": {"query": {"type": "string", "description": "A few key words, e.g. model tier latency"},
                                            "lesson_id": {"type": "string", "enum": lesson_ids(library),
                                                          "description": "Optional: search only this lesson, e.g. L1.3"}},
                             "required": ["query"]}}


def search_library(library, query, lesson_id=None, k=K):
    """The k best sections, of one lesson or of all, as search_result blocks with citations on."""
    if not query.strip():
        raise ValueError("the query is empty: send a few key words, e.g. model tier latency")
    if lesson_id is not None and lesson_id not in lesson_ids(library):
        raise ValueError(f"unknown lesson id {lesson_id!r}: ids look like L1.3, or leave lesson_id out to search them all")
    ranked = retrieve.search(library, query, k=len(retrieve.chunks(library)))   # one ranking, scored across the whole library
    found = [c for c in ranked if lesson_id is None or c["source"].startswith(lesson_id + "#")]
    return retrieve.as_results([{**c, "text": clean(c["text"])} for c in found[:k]])   # lesson text is data: cleaned


def section_of(library, lesson_id, quote):
    """The section a quote comes from, e.g. L1.3#the-three-tiers: the citation a saved question keeps."""
    for chunk in retrieve.chunks(library):
        if chunk["source"].startswith(lesson_id + "#") and words(quote) in words(chunk["text"]):
            return chunk["source"]
    return None
