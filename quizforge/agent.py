"""An agent loop with explicit stops. Claude picks the tools and their order; our code runs them, keeps count,
and decides when the loop ends."""
from dataclasses import dataclass, field

from quizforge import usage


class Stop(Exception):
    """A tool's decision that ends the task, such as a person's no. The loop sends no more requests."""


@dataclass
class Limits:
    max_turns: int = 8        # requests in one task
    max_usd: float = 0.05     # the task's budget: spent so far, plus the next request's worst case


@dataclass
class Outcome:
    stopped: str              # done, turn limit, budget, declined, refused, cut off
    turns: int
    text: str = ""
    calls: list = field(default_factory=list)
    peak: int = 0             # the largest input of any one request: how big the context got


def run(meter, cfg, system, tools, act, ask, limits=Limits(), out=print, **extra):
    """One task: loop until Claude ends its turn or a stop condition fires. Every tool_use gets a tool_result.
    extra: more request settings, passed to every request as they are (a beta header, for example)."""
    messages, calls, peak = [{"role": "user", "content": ask}], [], 0
    for turn in range(1, limits.max_turns + 1):
        counted = meter.count_tokens(model=cfg.model, system=system, tools=tools, messages=messages).input_tokens
        worst = usage.worst_case(meter.prices, cfg.model, counted, cfg.max_tokens)
        if meter.cost + worst > limits.max_usd:
            return Outcome("budget", turn - 1, f"spent ${meter.cost:.4f}; the next request could cost ${worst:.4f}", calls, peak)
        reply = meter.messages.create(model=cfg.model, max_tokens=cfg.max_tokens, system=system,
                                      tools=tools, messages=messages, **extra)
        peak = max(peak, reply.usage.input_tokens)
        text = "".join(block.text for block in reply.content if block.type == "text")
        uses = [block for block in reply.content if block.type == "tool_use"]
        out(f"  turn {turn}: {reply.stop_reason}, {[call.name for call in uses]}, ${meter.cost:.4f} so far")
        if reply.stop_reason == "end_turn":
            return Outcome("done", turn, text, calls, peak)
        if reply.stop_reason in ("refusal", "max_tokens"):
            return Outcome("refused" if reply.stop_reason == "refusal" else "cut off", turn, text, calls, peak)
        results = []
        for call in uses:
            calls.append(call.name)
            try:
                content, error = act(call)
            except Stop as stop:
                return Outcome(str(stop), turn, "", calls, peak)
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": content, "is_error": error})
        messages += [{"role": "assistant", "content": reply.content}, {"role": "user", "content": results}]
    return Outcome("turn limit", limits.max_turns, "", calls, peak)
