"""The approved bank, sealed: one SHA-256 line per approved file, written when a person approves (the same format as
sha256sum, so `sha256sum -c` reads it too). verify() runs before the bank is used: a file changed after approval, by
hand, by a tool or by an agent, no longer matches its line.
Usage: python -m quizforge.security.integrity [seal]"""

import hashlib
import sys
from pathlib import Path

from quizforge.config import ROOT

SEAL = "MANIFEST.sha256"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal(folder):
    """Write the manifest for every approved file. Only review.py calls it, after a person's yes."""
    lines = [f"{digest(p)}  {p.name}" for p in sorted(Path(folder).glob("*.json"))]
    (Path(folder) / SEAL).write_text("\n".join(lines) + "\n")
    return len(lines)


def verify(folder):
    """The problems: a file whose bytes changed, a file added without approval, a sealed file that is gone."""
    if not (Path(folder) / SEAL).exists():
        return [f"not sealed: no {SEAL} yet"]
    sealed = dict(reversed(line.split("  ", 1)) for line in (Path(folder) / SEAL).read_text().splitlines())
    now = {p.name: digest(p) for p in Path(folder).glob("*.json")}
    found = [f"changed after approval: {name}" for name in sorted(now) if name in sealed and now[name] != sealed[name]]
    found += [f"not approved: {name}" for name in sorted(now.keys() - sealed.keys())]
    found += [f"missing: {name}" for name in sorted(sealed.keys() - now.keys())]
    return found


if __name__ == "__main__":
    folder = ROOT / "bank/approved"
    if sys.argv[1:] == ["seal"]:  # a person's command, like eval --accept: review.py seals after each yes
        print(f"sealed {seal(folder)} approved file(s) in {SEAL}")
        sys.exit(0)
    problems = verify(folder)
    for line in problems:
        print(line)
    state = "FAILED" if problems else "all match the seal"
    n = len(list(folder.glob("*.json")))
    print(f"bank/approved: {n} file{'' if n == 1 else 's'}, {state}")
    sys.exit(1 if problems else 0)
