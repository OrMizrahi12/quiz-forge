from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = (ROOT / ".github" / "workflows" / "review.yml").read_text()


def test_the_key_comes_from_a_secret():
    assert "${{ secrets.ANTHROPIC_API_KEY }}" in WORKFLOW
    assert "sk-ant" not in WORKFLOW


def test_read_only_permissions():
    assert "permissions:\n  contents: read" in WORKFLOW


def test_review_runs_after_test():
    review = WORKFLOW.split("\n  review:\n")[1]
    assert "needs: test" in review and "timeout-minutes:" in review


def test_the_plugin_is_validated_before_any_review():
    test_job = WORKFLOW.split("\n  test:\n")[1].split("\n  review:\n")[0]
    assert "claude plugin validate ./plugin" in test_job


def test_the_headless_review_is_bounded():
    script = (ROOT / "scripts" / "ci_review.sh").read_text()
    for flag in (
        "--permission-mode dontAsk",
        "--allowedTools",
        "--max-turns",
        "--max-budget-usd",
        "--no-session-persistence",
    ):
        assert flag in script, flag
    assert "bypassPermissions" not in script and "dangerously" not in script
