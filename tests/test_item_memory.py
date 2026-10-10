import json
from dataclasses import replace

import pytest

from quizforge import memory, retrieve, write
from quizforge.config import load_config
from quizforge.sources import NotChecked

BASE = load_config()
OLD = (
    "A marketing team needs to generate 500 social media post captions per week, each 2-3 sentences long. The captions "
    "don't require deep reasoning, and the team wants to stay within its Pro plan's usage limits. Which model tier and "
    "effort level combination makes most sense?"
)
REWORDED = (
    "A marketing team must write 500 short social media captions each week. The captions need no deep reasoning, "
    "and the team wants to stay inside its Pro plan's usage limits. Which model tier and effort level fit best?"
)
OTHER = (
    "A data analyst writes one long, carefully argued strategy memo for the board next month, and accuracy matters "
    "more than speed. Which model tier should she start with?"
)


def a_sentence(lesson_id="L1.3"):
    """A line from one of the lesson's sections, so the quote check passes and the quote has a section."""
    return next(
        line.strip()
        for c in retrieve.chunks(BASE.library)
        if c["source"].startswith(lesson_id + "#")
        for line in c["text"].splitlines()
        if len(line.split()) > 10
    )


def question(scenario):
    return {
        "scenario": scenario,
        "a": "Haiku",
        "b": "Sonnet",
        "c": "Opus",
        "d": "Any of them",
        "answer": "A",
        "why": "The lesson says so.",
        "quote": a_sentence(),
    }


def put(bank, folder, lesson, *scenarios):
    path = bank / folder / f"{lesson}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"lesson": lesson, "questions": [question(s) for s in scenarios]}))
    return path


def test_overlap_is_shared_words_over_all_words():
    assert memory.overlap(OLD, OLD) == 1.0
    assert memory.overlap("Which tier fits the job?", "Which tier fits the job?".upper()) == 1.0
    assert memory.overlap("tier cost", "speed volume") == 0.0


def test_a_reworded_stem_is_over_the_threshold_and_a_new_situation_is_well_under():
    assert memory.overlap(OLD, REWORDED) >= BASE.similar
    assert memory.overlap(OLD, OTHER) < BASE.similar / 2


def test_item_memory_reads_pending_and_approved_but_not_declined(tmp_path):
    put(tmp_path, "pending", "L1.3", "pending stem?")
    put(tmp_path, "approved", "L1.3", "approved stem?")
    put(tmp_path, "declined", "L1.3", "declined stem?")
    assert memory.known_stems(tmp_path) == [("pending stem?", "pending/L1.3"), ("approved stem?", "approved/L1.3")]
    assert memory.known_stems(tmp_path, skip=tmp_path / "pending" / "L1.3.json") == [
        ("approved stem?", "approved/L1.3")
    ]


def test_a_duplicate_stem_is_flagged_with_what_to_do_instead(tmp_path):
    put(tmp_path, "approved", "L1.3", OLD)
    found = memory.repeats([OTHER, REWORDED], memory.known_stems(tmp_path), BASE.similar)
    assert len(found) == 1 and found[0].startswith("question 2: its scenario repeats one in approved/L1.3")
    assert "Write a different situation" in found[0]


def test_two_stems_in_the_same_save_cannot_repeat_each_other():
    found = memory.repeats([OLD, REWORDED], [], BASE.similar)
    assert len(found) == 1 and found[0].startswith("question 2:") and "this save (question 1)" in found[0]


def test_the_save_check_refuses_a_repeated_stem_and_writes_nothing(tmp_path):
    cfg = replace(BASE, bank=tmp_path)
    put(tmp_path, "approved", "L1.3", OLD)
    job = write.Job("L1.3", tmp_path / "pending" / "L1.3.json")
    with pytest.raises(NotChecked, match="repeats one in approved/L1.3"):
        write.save(cfg, job, "L1.3", [question(REWORDED), question(OTHER)])
    assert not job.path.exists() and job.saves == 0


def test_saving_again_does_not_count_the_jobs_own_draft_as_a_repeat(tmp_path):
    cfg = replace(BASE, bank=tmp_path)
    job = write.Job("L1.3", tmp_path / "pending" / "L1.3.json")
    write.save(cfg, job, "L1.3", [question(OLD), question(OTHER)])
    assert write.save(cfg, job, "L1.3", [question(OLD), question(OTHER)]).startswith("saved 2 questions")
    assert job.saves == 2 and all(q["section"].startswith("L1.3#") for q in job.questions)
