---
description: Writes exam-style practice questions for one course lesson into bank/pending/ and checks them. Also holds the checklist for judging a question. Use when asked to write, draft, add or review practice questions.
argument-hint: "[lesson-id]"
arguments: [lesson]
allowed-tools: Bash(.venv/bin/python ${CLAUDE_SKILL_DIR}/check_item.py *)
---

# Write an exam item

## The standard
- One situation of your own, and one clear question at the end.
- Four options, A to D. Exactly one is right; each wrong option is wrong for a reason the lesson gives.
- why says in one line why the answer is right.
- quote is one sentence copied word for word from the lesson; section is the lesson id, #, and the heading's anchor
  (check_item.py names the right one).

## Steps
1. Read library/ccao-f/v1/$lesson.md (the library path is in config.toml) and its objectives in MANIFEST.json.
2. Read bank/pending/ and bank/approved/ for $lesson, so you don't repeat a situation.
3. Add the new question to bank/pending/$lesson.json, the same shape as example-item.json. If the file exists,
   append to its questions list.
4. Run .venv/bin/python ${CLAUDE_SKILL_DIR}/check_item.py bank/pending/$lesson.json. Fix and rerun until it prints ok.

## Checklist for reviewers
Answer yes or no for each question:
1. Does the scenario end in one clear question?
2. Is exactly one option right, and is it the one in answer?
3. Is each wrong option wrong for a reason the lesson gives?
4. Is the quote word for word in the lesson?
5. Is the situation new, not a reworded one from the bank?
