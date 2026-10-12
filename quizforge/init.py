"""qf init: a deployment folder for another course library. It holds its own copy of the library, settings, prices,
model lock, prompts, eval cases, bank and logs; the code is installed once and QF_HOME says which deployment runs.
The writer prompt names its audience, so the deployment gets the next prompt version with its own audience, locked,
and its config points at it. The template's own versions are never edited."""

import json
import re
import shutil
from pathlib import Path

from quizforge.config import CODE
from quizforge.prompts import lock, versions

AUDIENCE = "people preparing for the Claude Certified Associate exam"  # the template's audience, in its prompt
CASES = 4  # eval cases: the library's first lessons


def init(folder, library, name, audience):
    folder, library = Path(folder).resolve(), Path(library).resolve()
    if folder.exists() and any(folder.iterdir()):
        raise SystemExit(f"{folder} is not empty")
    lessons = [row["lesson"] for row in json.loads((library / "MANIFEST.json").read_text())["lessons"]]
    folder.mkdir(parents=True, exist_ok=True)
    for rel in ("pricing.toml", "models.lock.toml", ".env.example", "evals/criteria.md"):
        (folder / rel).parent.mkdir(exist_ok=True)
        shutil.copy(CODE / rel, folder / rel)
    shutil.copytree(library, folder / "library")
    shutil.copytree(CODE / "prompts", folder / "prompts")
    writer = folder / "prompts/item_writer"
    latest = versions(writer)[-1]
    text = (writer / f"{latest}.md").read_text()
    assert AUDIENCE in text, f"the audience sentence moved in {latest}.md"
    mine = f"v{int(latest[1:]) + 1}"
    (writer / f"{mine}.md").write_text(text.replace(AUDIENCE, audience))
    lock(writer, mine)
    config = (CODE / "config.toml").read_text()
    config = re.sub(
        r'(?m)^path = "library/.*$',
        'path = "library"   # qf init: a copy of the library this deployment serves',
        config,
    )
    config = re.sub(
        r"(?m)^item_writer = .*$", f'item_writer = "{mine}"   # qf init: {latest} with this audience', config
    )
    (folder / "config.toml").write_text(f'[deployment]\nname = "{name}"\n\n' + config)
    (folder / "blueprint.toml").write_text(
        "# This deployment's exam blueprint (FR-2): one domain per exam domain, its weight, and the lessons that teach it.\n"
        "# qf init starts with one domain holding every lesson; split it to match your exam's blueprint.\n\n"
        f'[[domain]]\nname = "All lessons"\nweight = 100\nlessons = {json.dumps(lessons)}\n'
    )
    for case in ("cases.jsonl", "regression.jsonl"):
        (folder / "evals" / case).write_text(
            "".join(json.dumps({"lesson": lesson}) + "\n" for lesson in lessons[:CASES])
        )
    for sub in ("bank/pending", "bank/approved", "bank/declined", "runs"):
        (folder / sub).mkdir(parents=True)
    return [
        f"{name}: {folder}",
        f"library {library} ({len(lessons)} lessons)",
        f"prompt {mine}: {latest} for {audience}, locked",
        f"eval cases: {', '.join(lessons[:CASES])}",
        "blueprint: one domain, every lesson (edit blueprint.toml to match your exam)",
        f"next: put this deployment's key in {folder / '.env'}, then QF_HOME={folder} qf generate --lesson {lessons[0]}",
    ]
