import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def manifest(name):
    return json.loads((PLUGIN / name / ".claude-plugin" / "plugin.json").read_text())


def test_marketplace_lists_both_plugins():
    market = json.loads((PLUGIN / ".claude-plugin" / "marketplace.json").read_text())
    assert {p["name"] for p in market["plugins"]} == {"quiz-forge-tools", "qf-format"}
    for p in market["plugins"]:
        assert (PLUGIN / p["source"]).is_dir()


def test_both_plugins_have_semantic_versions():
    for name in ("quiz-forge-tools", "qf-format"):
        assert SEMVER.match(manifest(name)["version"]), name


def test_dependency_has_range():
    deps = {d["name"]: d["version"] for d in manifest("quiz-forge-tools")["dependencies"]}
    assert deps["qf-format"].startswith(("^", "~", ">=")), "a bare version pins; a range lets fixes in"
    major = manifest("qf-format")["version"].split(".")[0]
    assert deps["qf-format"].lstrip("^~>=").split(".")[0] == major, "the formatter moved past the range"


def test_hook_scripts_exist():
    for hooks_file in PLUGIN.glob("*/hooks/hooks.json"):
        plugin_root = hooks_file.parent.parent
        for groups in json.loads(hooks_file.read_text())["hooks"].values():
            for group in groups:
                for h in group["hooks"]:
                    assert "${CLAUDE_PLUGIN_ROOT}" in h["command"], h["command"]
                    script = re.search(r"\}\"?/(\S+\.py)", h["command"]).group(1)
                    assert (plugin_root / script).is_file(), f"{hooks_file}: {script}"


def test_the_reviewer_subagent_preloads_the_checklist_and_reads_only():
    text = (PLUGIN / "quiz-forge-tools" / "agents" / "item-reviewer.md").read_text()
    front = text.split("---")[1]
    assert "write-exam-item" in front
    assert re.search(r"^tools: Read, Glob, Grep$", front, re.M)
    assert re.search(r"^model: claude-[a-z0-9-]+-\d{8}$", front, re.M), "pin a dated model id"
