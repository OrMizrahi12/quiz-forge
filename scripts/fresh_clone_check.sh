#!/usr/bin/env bash
# The fresh clone: what a new team does with only the README. No API key needed.
# Clone into a temporary folder, a new venv, install, qf init on the sample library, the offline commands, the tests.
# Exits 1 on the first failing step. When a step fails, fix the README, not this script.
# Usage: bash scripts/fresh_clone_check.sh [repository]   (default: this checkout)
set -euo pipefail
REPO="${1:-$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

step() { echo "== $*"; }
fail() { echo "fresh clone: FAILED at: $*"; exit 1; }

step "git clone"
git clone -q "$REPO" "$TMP/quiz-forge" || fail "git clone"
cd "$TMP/quiz-forge"
step "venv and install (README: Install)"
python3 -m venv .venv || fail "venv"
.venv/bin/python -m pip install -q -e ".[dev]" || fail "pip install -e .[dev]"
step "qf --help"
.venv/bin/qf --help > /dev/null || fail "qf --help"
step "qf init on the sample library (README: Start a deployment)"
.venv/bin/qf init "$TMP/deploy/bakery" --library examples/sample-library/v1 --name bakery \
  --audience "home bakers learning to make bread" || fail "qf init"
export QF_HOME="$TMP/deploy/bakery"
step "qf plan --n 6"
.venv/bin/qf plan --n 6 || fail "qf plan"
step "qf bank"
.venv/bin/qf bank || fail "qf bank"
step "qf export --format csv (an empty bank: nothing to export yet)"
out="$(.venv/bin/qf export --format csv || true)"
[ "$out" = "nothing approved yet" ] || fail "qf export said: $out"
step "the platforms check"
.venv/bin/python -m quizforge.platforms > /dev/null || fail "python -m quizforge.platforms"
unset QF_HOME
step "the tests"
.venv/bin/python -m pytest -q || fail "pytest"
echo "fresh clone: ok"
