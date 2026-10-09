import hashlib
import re
from pathlib import Path

VERSION = re.compile(r"v(\d+)\.md")


class PromptChanged(Exception):
    """A locked version no longer matches its hash: someone edited it. Add the next version instead."""


def versions(folder: Path) -> list[str]:
    """The numbered versions in a prompt folder, oldest first: v1, v2, ... v10."""
    found = [(int(m.group(1)), m.group(0)[:-3]) for p in folder.glob("v*.md") if (m := VERSION.fullmatch(p.name))]
    return [name for _, name in sorted(found)]


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def locked(folder: Path) -> dict:
    """LOCK holds one line per measured version: the version and the SHA-256 of its text."""
    path = folder / "LOCK"
    if not path.exists():
        return {}
    return dict(line.split() for line in path.read_text().splitlines() if line.strip() and not line.startswith("#"))


def lock(folder: Path, version: str) -> str:
    """Freeze a version once it's measured. A locked version is never edited and never locked again."""
    text = (folder / f"{version}.md").read_text()
    if version in locked(folder):
        raise PromptChanged(f"{version} is already locked")
    with open(folder / "LOCK", "a") as f:
        f.write(f"{version} {digest(text)}\n")
    return digest(text)


def load_prompt(folder: Path, version: str) -> str:
    """The text of one version. It must be locked, and still match its hash."""
    known = versions(folder)
    if version not in known:
        raise ValueError(f"unknown prompt version {version!r}; {folder.name} has {', '.join(known)}")
    text = (folder / f"{version}.md").read_text()
    hashes = locked(folder)
    if version not in hashes:
        raise PromptChanged(f"{version} is not locked: measure it, then python -m quizforge prompts --lock {version}")
    if digest(text) != hashes[version]:
        raise PromptChanged(f"{version}.md changed after it was locked: restore it, and put the change in the next version")
    return text


def for_schema(text: str) -> str:
    """With structured outputs the schema sets the format, so the prompt's own <format> section goes.
    The same cut experiments/measure.py makes, so the prompt sent is the prompt that was measured."""
    return re.sub(r"<format>.*</format>", "", text, flags=re.S)
