"""How big is the stable part of generate's prompt (the system prompt and the lesson), per lesson? count_tokens is
free. Claude Haiku 4.5 caches a prefix only from 4,096 tokens: below that, cache_control is silently ignored."""
from quizforge.client import make_client
from quizforge.config import load_config
from quizforge.generate import user_turn
from quizforge.library import lesson_ids, load_lesson
from quizforge.prompts import for_schema, load_prompt

MINIMUM = 4096
cfg, client = load_config(), make_client()
system = for_schema(load_prompt(cfg.prompts, cfg.prompt))
sizes = {}
for lesson in lesson_ids(cfg.library):
    turn = user_turn(lesson, load_lesson(cfg.library, lesson), cfg.questions)
    sizes[lesson] = client.messages.count_tokens(model=cfg.model, system=system,
                                                 messages=[{"role": "user", "content": turn}]).input_tokens
for lesson, size in sorted(sizes.items(), key=lambda item: item[1]):
    print(f"{lesson:5} {size:6,} tokens  {'cacheable' if size >= MINIMUM else 'below the minimum: no cache'}")
