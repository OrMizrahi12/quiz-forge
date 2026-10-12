"""Key-shaped strings in what git is about to keep: the staged changes (the pre-commit hook), or with --history every
line ever committed. A finding is printed masked, never whole, and the exit code is 1.
Usage: python -m quizforge.security.secret_scan [--history]"""

import subprocess
import sys

from quizforge.security.redact import PATTERNS


def scan(diff):
    """(where, line, hint) for every added line that holds a key-shaped string; the hint is its first 7 characters."""
    hits, commit, path, line = [], "", None, 0
    for text in diff.splitlines():
        if text.startswith("commit "):
            commit = text.split()[1] + " "
        elif text.startswith("+++ "):
            path = text.removeprefix("+++ b/")
        elif text.startswith("@@"):
            line = int(text.split("+")[1].split(",")[0].split()[0]) - 1
        elif text.startswith("+"):
            line += 1
            hits += [(commit + path, line, m.group()[:7] + "...") for m in PATTERNS["KEY"].finditer(text)]
        elif not text.startswith("-"):
            line += 1
    return hits


if __name__ == "__main__":
    history = sys.argv[1:] == ["--history"]
    args = ["git", "log", "-p", "--all", "--format=commit %h"] if history else ["git", "diff", "--cached"]
    hits = scan(subprocess.run(args, capture_output=True, text=True, check=True).stdout)
    for where, line, hint in hits:
        print(f"{where}:{line}: a key-shaped string ({hint})")
    print(f"secret scan: {len(hits)} found in {'every commit' if history else 'the staged changes'}")
    sys.exit(1 if hits else 0)
