---
description: Drafts practice questions for a lesson and has them reviewed.
disable-model-invocation: true
argument-hint: "[lesson-id] [count]"
arguments: [lesson, count]
---

1. Use the write-exam-item skill to add $count new questions for $lesson to bank/pending/$lesson.json.
2. Ask the item-reviewer subagent to review bank/pending/$lesson.json.
3. List the new questions with the reviewer's verdicts.
4. End with: "Approval is python -m quizforge review, run by a person."
