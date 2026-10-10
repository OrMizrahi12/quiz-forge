import json
from dataclasses import replace

from quizforge import cli, review
from quizforge.config import load_config

BASE = load_config()


def pending(tmp_path, lesson, verdicts=("Question 1: supported",)):
    cfg = replace(BASE, bank=tmp_path)
    path = tmp_path / "pending" / f"{lesson}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    q = {
        "scenario": f"A {lesson} situation. What now?",
        "a": "1",
        "b": "2",
        "c": "3",
        "d": "4",
        "answer": "B",
        "why": "Because.",
        "quote": "A sentence from the lesson.",
        "section": f"{lesson}#the-idea",
    }
    path.write_text(
        json.dumps(
            {
                "lesson": lesson,
                "model": BASE.model,
                "prompt": "v4",
                "questions": [q],
                "verdicts": list(verdicts),
                "stopped": "done (checker, round 1)",
            }
        )
    )
    return cfg


def answers(*said):
    said = list(said)

    def ask(prompt):
        if not said:
            raise EOFError
        return said.pop(0)

    return ask


def quiet(cfg, ask, lessons=None):
    lines = []
    return review.review(cfg, lessons, ask=ask, out=lines.append), lines


def test_yes_moves_the_lesson_to_approved_with_its_verdicts(tmp_path):
    cfg = pending(tmp_path, "L1.3")
    decided, _ = quiet(cfg, answers("y"))
    kept = json.loads((tmp_path / "approved" / "L1.3.json").read_text())
    assert decided == {"L1.3": "approved"} and not (tmp_path / "pending" / "L1.3.json").exists()
    assert kept["questions"][0]["verdict"] == "supported" and kept["questions"][0]["approved"]


def test_no_moves_the_lesson_to_declined(tmp_path):
    cfg = pending(tmp_path, "L2.2")
    decided, _ = quiet(cfg, answers("n"))
    assert decided == {"L2.2": "declined"} and (tmp_path / "declined" / "L2.2.json").exists()
    assert not (tmp_path / "approved").exists()


def test_nothing_is_approved_without_a_yes(tmp_path):
    pending(tmp_path, "L1.3")
    cfg = pending(tmp_path, "L2.2")
    decided, _ = quiet(cfg, answers("", "ok"))
    assert decided == {"L1.3": "pending", "L2.2": "pending"} and not (tmp_path / "approved").exists()
    assert len(review.pending(cfg)) == 2


def test_with_no_one_to_answer_it_stops_and_leaves_everything_pending(tmp_path):
    pending(tmp_path, "L1.3")
    cfg = pending(tmp_path, "L2.2")
    decided, _ = quiet(cfg, answers())
    assert decided == {"L1.3": "pending"} and len(review.pending(cfg)) == 2


def test_one_lesson_at_a_time_in_order_and_approved_questions_add_up(tmp_path):
    pending(tmp_path, "L2.2")
    cfg = pending(tmp_path, "L1.3")
    decided, _ = quiet(cfg, answers("y", "n"))
    assert list(decided.items()) == [("L1.3", "approved"), ("L2.2", "declined")]
    pending(tmp_path, "L1.3")
    quiet(cfg, answers("yes"), lessons=["L1.3"])
    assert len(json.loads((tmp_path / "approved" / "L1.3.json").read_text())["questions"]) == 2


def test_the_person_sees_each_question_its_citation_and_the_checkers_verdict(tmp_path):
    cfg = pending(tmp_path, "L1.3", verdicts=["Question 1: not supported: the quote is about cost"])
    _, lines = quiet(cfg, answers("n"))
    shown = "\n".join(lines)
    assert "Quote (L1.3#the-idea)" in shown and "Checker: not supported: the quote is about cost" in shown
    assert "warning: the checker did not support every question" in shown


def test_counts_pending_and_approved_per_lesson(tmp_path):
    pending(tmp_path, "L2.2")
    cfg = pending(tmp_path, "L1.3")
    quiet(cfg, answers("y"), lessons=["L1.3"])
    pending(tmp_path, "L1.3")
    pending(tmp_path, "L3.1")
    assert review.counts(cfg) == {
        "L1.3": {"pending": 1, "approved": 1},
        "L2.2": {"pending": 1, "approved": 0},
        "L3.1": {"pending": 1, "approved": 0},
    }
    assert list(review.counts(cfg)) == ["L1.3", "L2.2", "L3.1"]


def test_counts_on_an_empty_bank_is_empty(tmp_path):
    assert review.counts(replace(BASE, bank=tmp_path)) == {}


def test_counts_does_not_touch_the_bank(tmp_path):
    cfg = pending(tmp_path, "L1.3")
    before = sorted((p, p.read_text()) for p in tmp_path.rglob("*") if p.is_file())
    review.counts(cfg)
    assert sorted((p, p.read_text()) for p in tmp_path.rglob("*") if p.is_file()) == before
    assert not (tmp_path / "approved").exists()


def test_bank_prints_a_line_per_lesson_and_a_total(tmp_path, capsys):
    cfg = pending(tmp_path, "L2.2")
    quiet(pending(tmp_path, "L1.3"), answers("y"), lessons=["L1.3"])
    cli.show_bank(cfg)
    lines = capsys.readouterr().out.splitlines()
    assert [line.split() for line in lines] == [
        ["L1.3", "pending", "0", "approved", "1"],
        ["L2.2", "pending", "1", "approved", "0"],
        ["total", "pending", "1", "approved", "1"],
    ]
    cli.show_bank(replace(BASE, bank=tmp_path / "nowhere"))
    assert capsys.readouterr().out == "bank is empty\n"
