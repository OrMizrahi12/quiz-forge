import re
import sys

import anthropic
from dotenv import load_dotenv

from quizforge.repair import Refused, RepairFailed, write_checked

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-haiku-4-5-20251001"
RULES = open("prompts/item_writer/system.md").read()
RULES = re.sub(r"<format>.*</format>", "", RULES, flags=re.S)
lesson = open("library/ccao-f/v1/L2.1.md").read()
ASK = f'<lesson id="L2.1">\n{lesson}\n</lesson>\n\nWrite 2 questions.'

runs = int(sys.argv[1])
max_tokens = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
first = repaired = failed = 0
for run in range(1, runs + 1):
    print(f"run {run}")
    try:
        data, attempts = write_checked(client, MODEL, RULES, ASK, lesson, 2,
                                       max_tokens=max_tokens)
    except (Refused, RepairFailed) as error:
        failed += 1
        print(f"  FAILED: {error}")
        continue
    first, repaired = first + (attempts == 1), repaired + (attempts > 1)
print(f"== first try {first}/{runs}, repaired {repaired}/{runs}, failed {failed}/{runs}")
