"""A supervisor and its subagents: the supervisor writes a brief per lesson and delegates; each subagent starts with a clean
context (its brief only), does the work with the writer's tools, and hands back one line. Our code runs them in parallel."""
from concurrent.futures import ThreadPoolExecutor

from quizforge import agent, writer_tools

DELEGATE = {"name": "delegate",
            "description": "Hands one lesson to a subagent that starts with an empty context. The brief is all it sees, so "
                           "say the lesson id, how many questions, the tools to use (read_lesson, check_quote, "
                           "save_questions) and what to report back. Returns the subagent's one-line report. Call it "
                           "once per lesson; calls in the same turn run in parallel.",
            "input_schema": {"type": "object",
                             "properties": {"lesson_id": {"type": "string"}, "brief": {"type": "string"}},
                             "required": ["lesson_id", "brief"]}}


def subagent(meter, cfg, system, approve, brief, limits):
    """A clean context: the brief is the whole conversation so far."""
    result = agent.run(meter, cfg, system, writer_tools.tools(cfg), writer_tools.act(cfg, approve), brief, limits,
                       out=lambda line: None)
    return f"{result.stopped} after {result.turns} turn(s): {' '.join(result.text.split())[:200] or 'no text'}"


def supervise(meters, cfg, system, approve, ask, limits=agent.Limits(max_turns=4, max_usd=0.10),
              worker_limits=agent.Limits(max_turns=8, max_usd=0.08)):
    """The supervisor's loop: its delegate calls in one turn run at the same time, each subagent on its own meter."""
    lead = meters()
    messages, reports = [{"role": "user", "content": ask}], []
    for turn in range(limits.max_turns):
        reply = lead.messages.create(model=cfg.model, max_tokens=cfg.max_tokens, system=SUPERVISOR,
                                     tools=[DELEGATE], messages=messages)
        calls = [b for b in reply.content if b.type == "tool_use"]
        if reply.stop_reason != "tool_use":
            return lead, reports, "".join(b.text for b in reply.content if b.type == "text")
        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            jobs = [(call, meters()) for call in calls]
            done = [pool.submit(subagent, m, cfg, system, approve, call.input["brief"], worker_limits) for call, m in jobs]
            results = []
            for (call, m), job in zip(jobs, done):
                report = job.result()
                reports.append((call.input["lesson_id"], m, report))
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": report})
        messages += [{"role": "assistant", "content": reply.content}, {"role": "user", "content": results}]
    return lead, reports, "turn limit"


SUPERVISOR = ("You supervise question writers. You don't write questions yourself: for each lesson in the request, call "
              "delegate once, with a short self-contained brief. Put all the delegate calls in one turn. When the "
              "reports are back, answer with one line per lesson: saved or not, and why.")
