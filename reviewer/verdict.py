"""The one verdict shape every reviewer returns: the Agent SDK reviewer validates into it, and the headless CI review
sends verdict.schema.json, which is generated from it. Never edit the schema file by hand:
python -m reviewer.verdict > reviewer/verdict.schema.json"""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(description="The pending file's lesson id, e.g. L1.3")
    verdict: Literal["pass", "fail"]
    reasons: list[str] = Field(description="One line per problem found")
    rule: str | None = Field(description="The rule or checklist line broken, or null")


def schema():
    return Verdict.model_json_schema()


if __name__ == "__main__":
    print(json.dumps(schema(), indent=2))
