from quizforge.security.secret_scan import scan

KEY = "sk-ant-" + "api03-" + "x" * 24  # built at runtime: no key-shaped literal in the repository
DIFF = f"""diff --git a/notes.txt b/notes.txt
+++ b/notes.txt
@@ -0,0 +1,3 @@
+first line
+ANTHROPIC_API_KEY={KEY}
+third line
"""


def test_a_key_is_found_with_its_place_and_a_masked_hint():
    assert scan(DIFF) == [("notes.txt", 2, "sk-ant-...")]


def test_the_hint_never_holds_the_key():
    assert all(KEY not in hint for _, _, hint in scan(DIFF))


def test_ordinary_lines_are_not_flagged():
    assert scan(DIFF.replace(KEY, "paste-your-key-here")) == []


def test_history_names_the_commit():
    assert scan("commit abc1234\n" + DIFF)[0][0] == "abc1234 notes.txt"
