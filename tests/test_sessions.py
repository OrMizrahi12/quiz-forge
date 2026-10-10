import asyncio
import json

import pytest

from reviewer import sdk_review


def test_ask_refuses_another_items_session(tmp_path, monkeypatch):
    monkeypatch.setattr(sdk_review, "RUNS", tmp_path)
    saved = {"verdict": {"item_id": "L2.1"}, "session_id": "s-2"}
    (tmp_path / "L1.3.json").write_text(json.dumps(saved))
    with pytest.raises(SystemExit):
        asyncio.run(sdk_review.ask("L1.3", "Why?"))
