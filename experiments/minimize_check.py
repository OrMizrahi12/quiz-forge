"""What the writer would be sent for the privacy fixture, before and after minimize(): the input tokens (count_tokens,
which is free) and how many email addresses, phone numbers and keys are in the text. Counts only."""

from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.sanitize import minimize
from quizforge.security.redact import found

cfg = load_config()
client = make_client()
raw = (ROOT / "library/fixtures/pii/L2.1.md").read_text()
for name, text in (("as written", raw), ("minimized", minimize(raw))):
    tokens = client.messages.count_tokens(model=cfg.model, messages=[{"role": "user", "content": text}]).input_tokens
    counts = "  ".join(f"{kind.lower()} {n}" for kind, n in found(text).items())
    print(f"{name:11} {tokens:5} input tokens   {counts}")
