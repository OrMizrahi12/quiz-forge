import json
from usage import call

MODEL = "claude-haiku-4-5-20251001"
lesson = open("library/ccao-f/v1/L1.3.md").read()
done = 0
for task in range(1, 6):
    q = call(
        f"task {task} write",
        MODEL,
        400,
        "You write quiz questions.",
        [
            {
                "role": "user",
                "content": "Write one multiple-choice quiz question about this lesson: four options, then the answer letter.\n\n"
                + lesson,
            }
        ],
    )
    c = call(
        f"task {task} check",
        MODEL,
        5,
        "You check quiz questions.",
        [
            {
                "role": "user",
                "content": "Is this question answered by the lesson, with the right answer letter? Reply PASS or FAIL.\n\n"
                + lesson
                + "\n\nQUESTION:\n"
                + q.content[0].text,
            }
        ],
    )
    done += c.content[0].text.strip("* \n").startswith("PASS")

rows = [json.loads(line) for line in open("runs/usage.jsonl") if '"task' in line]
spent = sum(row["cost"] for row in rows)
print(f"\n{len(rows)} requests: ${spent:.5f}, ${spent / len(rows):.5f} per request")
print(f"{done} of 5 questions passed: ${spent / done:.5f} per completed task")
