"""Personal data and secrets, found and replaced before text is stored. The patterns are simple on purpose: they catch
the common shapes (an email address, a phone number, an API key) and leave a placeholder that says what was there."""

import re

PATTERNS = {
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
    "PHONE": re.compile(r"(?<!\w)(?:\+\d{1,3}[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b"),
    "KEY": re.compile(r"\bsk-ant-[\w-]{8,}|\bBearer [\w.~+/-]{16,}"),
}


def redact(text):
    """Each match becomes a placeholder: [EMAIL], [PHONE], [KEY]."""
    for name, pattern in PATTERNS.items():
        text = pattern.sub(f"[{name}]", text)
    return text


def redact_obj(obj):
    """The same through dicts and lists: a saved reply, a JSON row."""
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, dict):
        return {key: redact_obj(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [redact_obj(value) for value in obj]
    return obj


def found(text):
    """How many of each, never the matches themselves."""
    return {name: len(pattern.findall(text)) for name, pattern in PATTERNS.items()}
