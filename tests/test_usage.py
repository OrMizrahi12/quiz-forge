import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from quizforge import usage
from quizforge.config import ROOT

PRICES = usage.load_prices(ROOT / "pricing.toml")
CASES = json.loads((Path(__file__).parent / "fixtures" / "usage.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_cost_matches_the_fixture(case):
    assert usage.cost(PRICES, case["model"], SimpleNamespace(**case["usage"])) == pytest.approx(case["cost"], abs=1e-9)


def test_worst_case_is_counted_input_plus_max_tokens():
    # 4,376 counted input tokens and max_tokens 1,500 on Haiku 4.5: $0.004376 + $0.0075
    assert usage.worst_case(PRICES, "claude-haiku-4-5-20251001", 4376, 1500) == pytest.approx(0.011876)


def test_log_writes_one_json_line_with_every_field(tmp_path):
    path = tmp_path / "runs" / "usage.jsonl"
    row = dict(
        time="2026-10-08T12:00:00+00:00",
        label="L1.3 generate",
        model="claude-haiku-4-5-20251001",
        request_id="req_test",
        counted=4376,
        input=4376,
        cache_write=0,
        cache_read=0,
        output=159,
        cost=0.005171,
        seconds=3.2,
    )
    usage.log(path, **row)
    usage.log(path, **row)
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert list(json.loads(lines[0])) == list(usage.FIELDS)


def test_log_refuses_a_row_with_a_missing_field(tmp_path):
    with pytest.raises(ValueError, match="request_id"):
        usage.log(
            tmp_path / "usage.jsonl",
            time="t",
            label="x",
            model="m",
            counted=1,
            input=1,
            cache_write=0,
            cache_read=0,
            output=1,
            cost=0.0,
            seconds=0.1,
        )


def test_summary_adds_up_by_lesson(tmp_path):
    path = tmp_path / "usage.jsonl"
    base = dict(
        time="t", model="m", request_id="r", counted=1, input=1, cache_write=0, cache_read=0, output=1, seconds=1.0
    )
    usage.log(path, label="L1.3 generate", cost=0.01, **base)
    usage.log(path, label="L1.3 generate", cost=0.02, **base)
    usage.log(path, label="L2.1 generate", cost=0.03, **base)
    s = usage.summary(path)
    assert s["requests"] == 3 and s["cost"] == pytest.approx(0.06)
    assert s["by_lesson"] == pytest.approx({"L1.3": 0.03, "L2.1": 0.03})
