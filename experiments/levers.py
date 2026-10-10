from usage import call

lesson = open("library/ccao-f/v1/L1.3.md").read()
ASK = [
    {
        "role": "user",
        "content": "Write one multiple-choice quiz question about the lesson: four options, the answer letter, and a short explanation.",
    }
]
SHORT = [
    {
        "role": "user",
        "content": "Write one multiple-choice quiz question about the lesson: four options and the answer letter only.",
    }
]
CACHED = [{"type": "text", "text": lesson, "cache_control": {"type": "ephemeral"}}]

call("baseline", "claude-haiku-4-5-20251001", 1000, lesson, ASK)
call("cache write", "claude-haiku-4-5-20251001", 1000, CACHED, ASK)
call("cache read", "claude-haiku-4-5-20251001", 1000, CACHED, ASK)
call("short output", "claude-haiku-4-5-20251001", 200, CACHED, SHORT)
call("Haiku 5.5", "claude-haiku-5-5", 1000, lesson, ASK)
call("effort low", "claude-haiku-5-5", 1000, lesson, ASK, output_config={"effort": "low"})
