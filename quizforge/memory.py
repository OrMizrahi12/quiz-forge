"""Two kinds of agent memory.
The memory tool's client side: Claude asks for file operations under /memories, our code runs them in one folder per scope,
refuses any path outside it, and caps how big a file may grow (memory is read at the start of every task).
Item memory: our own store of every stem in the bank, so a new question can't repeat an old one. The rule is known in
advance, so code enforces it at the save; Claude doesn't have to remember it."""
import json
import shutil
from pathlib import Path

from quizforge.retrieve import words

TOOL = {"type": "memory_20250818", "name": "memory"}
CAP = 1500   # characters per file: a memory that grows without limit becomes context bloat


class Memory:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, p):
        """/memories/x -> root/x; anything that resolves outside root is refused (../, links, encoded tricks)."""
        if not p.startswith("/memories"):
            raise ValueError(f"The path {p} is outside /memories")
        real = (self.root / p.removeprefix("/memories").lstrip("/")).resolve()
        if real != self.root and self.root not in real.parents:
            raise ValueError(f"The path {p} is outside /memories")
        return real

    def run(self, c):
        p = self.path(c.get("path") or c.get("old_path"))
        if c["command"] == "view":
            if p.is_dir():
                rows = [f"{f.stat().st_size}\t/memories/{f.relative_to(self.root)}" for f in sorted(p.rglob("*")) if f.is_file()]
                return "\n".join([f"Here're the files and directories up to 2 levels deep in {c['path']}:"] + rows)
            if not p.exists():
                raise ValueError(f"The path {c['path']} does not exist. Please provide a valid path.")
            lines = p.read_text().splitlines()
            return f"Here's the content of {c['path']} with line numbers:\n" + "\n".join(f"{n:6}\t{l}" for n, l in enumerate(lines, 1))
        if c["command"] == "create":
            return self.write(p, c["file_text"], f"File created successfully at: {c['path']}")
        if c["command"] == "str_replace":
            text = p.read_text()
            if text.count(c["old_str"]) != 1:
                raise ValueError(f"No replacement was performed: old_str must appear exactly once in {c['path']}.")
            return self.write(p, text.replace(c["old_str"], c.get("new_str", "")), "The memory file has been edited.")
        if c["command"] == "insert":
            lines = p.read_text().splitlines(keepends=True)
            lines.insert(c["insert_line"], c["insert_text"])
            return self.write(p, "".join(lines), f"The file {c['path']} has been edited.")
        if c["command"] == "delete":
            if p == self.root:
                raise ValueError("The memory directory itself can't be deleted")
            shutil.rmtree(p) if p.is_dir() else p.unlink()
            return f"Successfully deleted {c['path']}"
        if c["command"] == "rename":
            p.rename(self.path(c["new_path"]))
            return f"Renamed {c['old_path']} to {c['new_path']}"
        raise ValueError(f"Unknown command {c['command']}")

    def write(self, p, text, ok):
        if len(text) > CAP:
            raise ValueError(f"Not saved: memory files are capped at {CAP} characters ({len(text)} given). Keep only what a "
                             "later task needs: shorten or replace older notes.")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return ok

    def size(self):
        return sum(f.stat().st_size for f in self.root.rglob("*") if f.is_file())


REMEMBERED = ("pending", "approved")   # the bank folders item memory reads; declined questions are free to try again


def stem_words(stem):
    """The words that carry meaning: common words dropped, plurals folded (the search's own words())."""
    return set(words(stem))


def overlap(a, b):
    """Shared words over all the words of both stems (Jaccard): 1.0 the same words, 0.0 none in common."""
    x, y = stem_words(a), stem_words(b)
    return len(x & y) / len(x | y) if x | y else 0.0


def known_stems(bank, skip=None):
    """(stem, where) for every question in bank/pending and bank/approved. skip: a file to leave out, the job's own draft."""
    found = []
    for folder in REMEMBERED:
        for path in sorted((Path(bank) / folder).glob("*.json")):
            if skip is None or path.resolve() != Path(skip).resolve():
                found += [(q["scenario"], f"{folder}/{path.stem}") for q in json.loads(path.read_text())["questions"]]
    return found


def repeats(stems, known, limit):
    """A problem line for each new stem too close to a known stem, or to an earlier stem in the same save."""
    found, earlier = [], []
    for n, stem in enumerate(stems, 1):
        for old, where in known + earlier:
            score = overlap(stem, old)
            if score >= limit:
                found.append(f"question {n}: its scenario repeats one in {where} ({score:.0%} of the words shared: "
                             f"{' '.join(old.split()[:12])} ...). Write a different situation, not a reworded one")
                break
        earlier.append((stem, f"this save (question {n})"))
    return found
