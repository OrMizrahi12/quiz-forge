import re
import unicodedata

TAG = re.compile(r"<\s*/?\s*lesson\b[^>]*>", re.I)


def clean(text):
    """A lesson is untrusted text: drop invisible characters and any lesson tag inside it."""
    text = "".join(c for c in text if c in "\n\t" or unicodedata.category(c)[0] != "C")
    return TAG.sub("", text)
