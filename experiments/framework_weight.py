"""What would each framework add to this project? pip resolves the install without doing it (--dry-run) and reports every
package it would bring in, and any package we already have that it would change."""
import json
import subprocess
import sys

FRAMEWORKS = ["pydantic-ai-slim[anthropic]", "langgraph", "strands-agents[anthropic]"]
have = {line.split("==")[0].lower(): line.split("==")[1] for line in open("requirements.txt").read().split() if "==" in line}

for name in FRAMEWORKS:
    report = subprocess.run([sys.executable, "-m", "pip", "install", "--dry-run", "--quiet", "--report", "-", name],
                            capture_output=True, text=True, check=True).stdout
    added = [(p["metadata"]["name"].lower(), p["metadata"]["version"]) for p in json.loads(report)["install"]]
    changed = [f"{n} {have[n]} -> {v}" for n, v in added if n in have]
    print(f"{name:28} {len(added) - len(changed):2} new packages; changes ours: {', '.join(changed) or 'none'}")
