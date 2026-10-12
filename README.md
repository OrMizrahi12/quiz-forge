# Quiz Forge

Practice exam questions from any course library. Code checks every question, a calibrated judge grades them, and a
person approves each one before learners see it.

## Install

```
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"   # dev: pytest and ruff, for the tests
```

## Start a deployment for your library

A library is a folder with `MANIFEST.json` and one `<lesson>.md` per lesson (see `examples/sample-library/v1`).

```
.venv/bin/qf init ~/qf-deploy/bakery --library examples/sample-library/v1 --name bakery --audience "home bakers learning to make bread"
cp .env.example ~/qf-deploy/bakery/.env      # then put this deployment's API key in it
QF_HOME=~/qf-deploy/bakery .venv/bin/qf generate --lesson B1.1
```

## Check it

- Tests: `.venv/bin/python -m pytest -q`
- The deployment's evals: `QF_HOME=<folder> .venv/bin/python -m evals.run --max-usd 0.05`
- What is running: `QF_HOME=<folder> .venv/bin/python -m quizforge.release`

Docs: `docs/deployments.md`, `docs/runbook.md`, `CONTRIBUTING.md`, `CHANGELOG.md`.
