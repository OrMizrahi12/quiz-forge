# Contributing to Quiz Forge

1. Open an issue first: what is wrong or missing, how to reproduce it, and the version (`python -m quizforge.release`).
2. Work on a branch. Run `python -m pytest -q` before you push.
3. Open a pull request that says `Closes #<issue>`. CI runs the tests, the secret scan, and the eval gate when
   prompts, models or `quizforge/` change. A person merges.
4. A model or prompt change needs evidence in the pull request: the evals, against the baseline (docs/runbook.md).
5. Add a line to `CHANGELOG.md` under the next version.

Security problems are never filed as public issues: email the maintainer instead.
