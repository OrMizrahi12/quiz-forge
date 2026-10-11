import re
import unicodedata

from quizforge.security.redact import redact

TAG = re.compile(r"<\s*/?\s*lesson\b[^>]*>", re.I)
# sections the writer never needs
NOT_NEEDED = re.compile(r"^## Reader questions\n.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)


def clean(text):
    """A lesson is untrusted text: drop invisible characters and any lesson tag inside it, then minimize it."""
    text = "".join(c for c in text if c in "\n\t" or unicodedata.category(c)[0] != "C")
    return minimize(TAG.sub("", text))


def minimize(text):
    """Send only what the task needs: drop the sections the writer never uses, then mask what is left."""
    return redact(NOT_NEEDED.sub("", text))
