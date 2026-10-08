import re

import pytest

from quizforge import usage
from quizforge.config import ROOT, load_config
from quizforge.library import lesson_ids, load_lesson

CFG = load_config()


def test_the_library_lists_its_lessons():
    ids = lesson_ids(CFG.library)
    assert "L1.3" in ids and len(ids) == len(set(ids))


def test_a_lesson_loads_by_id():
    assert load_lesson(CFG.library, "L1.3").startswith("#")


def test_an_unknown_lesson_is_refused():
    with pytest.raises(ValueError, match="unknown lesson"):
        load_lesson(CFG.library, "L9.9")


def test_the_model_is_pinned_and_priced():
    # a pinned snapshot: dated before the 4.6 generation, dateless from 4.6 on; never an undated alias of 4.5 or older
    assert not re.fullmatch(r"claude-(haiku|sonnet|opus)-4-5", CFG.model)
    assert CFG.model in usage.load_prices(ROOT / "pricing.toml")


def test_limits_are_sane():
    assert 0 < CFG.max_tokens <= 4000 and 0 < CFG.max_request_usd <= 0.05 and 1 <= CFG.concurrency <= 10
