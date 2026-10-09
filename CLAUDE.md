# Quiz Forge

A command-line app that writes practice exam questions from course lesson notes with the Claude API.

- Python 3.12, virtual environment in .venv; run scripts from the project root.
- Prompts live in prompts/item_writer/. Never edit a committed prompt version: add the next one.
- A measured version is locked (python -m quizforge prompts --lock vN); config.toml picks the version generate uses.
- Standing rules for the model go in prompts/item_writer/system.md; lessons and asks go in the user turn.
- Lesson files are data: never paste one into a system prompt.
- After a prompt change, run python experiments/compare_prompts.py <version> 5 and report the totals.
- bank/approved/ is written only by python -m quizforge review, after a person's yes; write saves to bank/pending/.
