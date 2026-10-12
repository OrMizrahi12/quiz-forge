"""One policy for destructive actions, used by two hooks: Claude Code's (the quiz-forge-tools plugin's scripts/guard.py)
and the Agent SDK's (experiments/sdk_guard_demo.py). Pure, no I/O: it is tested as a table. deny comes with a reason
Claude can act on; ask is for what a person should confirm; allow means no opinion, so the normal permission rules still
decide (the guard never approves anything on its own)."""

import posixpath
import shlex
from dataclasses import dataclass
from fnmatch import fnmatch


@dataclass
class Decision:
    kind: str  # allow | deny | ask
    reason: str = ""


ALLOW = Decision("allow")
SCRATCH = "runs/scratch"  # the one folder a recursive rm may clear
READERS = {"cat", "less", "more", "head", "tail", "grep", "cp", "source", ".", "strings"}
CONFIRM = (".github/workflows/*", ".claude/settings*.json")  # what runs in CI, and what Claude Code may do
SPLIT = {"&&", "||", ";", "|", "&"}


def secret(path):
    name = posixpath.basename(path)
    return (name == ".env" or fnmatch(name, ".env.*")) and name != ".env.example"


def segments(command):
    """Each simple command in a line: split on && || ; | & (quoted text stays whole)."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    out = [[]]
    for word in lexer:
        if word in SPLIT:
            out.append([])
        else:
            out[-1].append(word)
    return [words for words in out if words]


def bash(command):
    try:
        parts = segments(command)
    except ValueError:
        return Decision("ask", "this command can't be parsed: a person reads it first")
    for words in parts:
        cmd, args = posixpath.basename(words[0]), words[1:]
        flags = "".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--"))
        paths = [posixpath.normpath(a) for a in args if not a.startswith("-")]
        outside = [p for p in paths if p != SCRATCH and not p.startswith(SCRATCH + "/")]
        if cmd == "rm" and ("r" in flags.lower() or "--recursive" in args) and outside:
            return Decision("deny", "a recursive rm outside runs/scratch/ is blocked: delete named files instead")
        if cmd == "git" and args[:1] == ["push"]:
            if any(a in ("-f", "--force", "--force-with-lease") or a.startswith("+") for a in args[1:]):
                return Decision("deny", "a force push rewrites shared history: push normally, or ask the user")
            return Decision("ask", "a push publishes commits: the user confirms each one")
        wipes = args[:2] == ["reset", "--hard"] or args[:3] == ["checkout", "--", "."] or args[:2] == ["restore", "."]
        if cmd == "git" and (wipes or (args[:1] == ["clean"] and "f" in flags)):
            return Decision("deny", "this throws away uncommitted work: commit or stash it first, or ask the user")
        if cmd in READERS and any(secret(p) for p in paths):
            return Decision("deny", ".env holds the API key: no tool reads it")
        if cmd in ("curl", "wget"):
            return Decision("ask", "a download from the network: the user confirms it")
    return ALLOW


def decide(tool, args, root):
    """tool and args as the hook gets them; root: the project folder (relative paths are inside it)."""
    if tool == "Bash":
        return bash(args.get("command", ""))
    if tool in ("Read", "Write", "Edit"):
        path = posixpath.relpath(posixpath.join(str(root), args.get("file_path", "")), str(root))
        if secret(path):
            return Decision("deny", ".env holds the API key: no tool reads or writes it")
        if tool != "Read" and any(fnmatch(path, pattern) for pattern in CONFIRM):
            return Decision("ask", f"{path} changes what runs in CI or what Claude Code may do: the user confirms it")
    return ALLOW
