"""Who is calling: the credential this process uses, by name and by source (never its value), and the workspace the
API puts its requests in. One count_tokens request, which is free. Usage: python -m quizforge.whoami"""

import os

from dotenv import dotenv_values

from quizforge.client import make_client
from quizforge.config import ROOT, load_config

NAME = "ANTHROPIC_API_KEY"


def source():
    """Where the key comes from, checked before .env is loaded: the environment wins over the file."""
    if NAME in os.environ:
        return "the environment"
    return ".env" if NAME in dotenv_values(ROOT / ".env") else "nowhere: put it in .env"


if __name__ == "__main__":
    where, cfg = source(), load_config()
    asked = {"model": cfg.model, "messages": [{"role": "user", "content": "Who am I?"}]}
    reply = make_client().messages.with_raw_response.count_tokens(**asked)
    print(f"credential   {NAME}, from {where} (its value is never printed)")
    print(f"workspace    {reply.headers.get('anthropic-workspace-id')}")
    print(f"request id   {reply.headers.get('request-id')}")
    print(f"checked with count_tokens on {cfg.model}: free")
