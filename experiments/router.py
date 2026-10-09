"""The router pattern, three ways: classify a request, then send it down the right path. Our own code, Pydantic AI, and
LangGraph. Same model, same requests, same paths; what differs is who wires them."""
import time
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from pydantic_ai import Agent

from quizforge import sources, usage
from quizforge.client import make_client
from quizforge.config import load_config

cfg = load_config()
prices = usage.load_prices("pricing.toml")
client = make_client()
ROUTER = ("You route requests for the Quiz Forge course tutor. kind 'check' when the request asks whether a quote comes "
          "from a lesson (copy the lesson id and the quote exactly); 'write' when it asks for a practice question (the "
          "topic); 'other' for anything else.")
REQUESTS = ["Is this really from lesson L1.3: 'Start with the smallest tier that can clearly do the job.'?",
            "Write me a practice question about prompt caching.",
            "Does L2.2 say 'Break the task into steps you can check one at a time'?",
            "What's the weather like in Tel Aviv today?"]


class Route(BaseModel):
    kind: Literal["check", "write", "other"]
    lesson_id: str = ""
    quote: str = ""
    topic: str = ""


def act(route):
    """The paths: the same plain functions for every way."""
    if route.kind == "check":
        return sources.check_quote(cfg.library, route.lesson_id, route.quote)
    if route.kind == "write":
        return f"queued: a practice question about {route.topic}"
    return "not something the tutor does"


# 1. Our own code: one structured call, then an if.
def ours(request):
    reply = client.messages.parse(model=cfg.model, max_tokens=300, system=ROUTER, output_format=Route,
                                  messages=[{"role": "user", "content": request}])
    return reply.parsed_output, reply.usage


# 2. Pydantic AI: an agent whose output type is the route.
router = Agent(f"anthropic:{cfg.model}", output_type=Route, instructions=ROUTER)

def pydantic_ai(request):
    result = router.run_sync(request)
    return result.output, result.usage   # its own usage object: the same token counts, other names for the rest


# 3. LangGraph: a graph whose first node classifies, and whose edge picks the next node.
class State(TypedDict):
    request: str
    route: Route
    usage: object
    answer: str

def classify(state):
    route, used = ours(state["request"])
    return {"route": route, "usage": used}

graph = StateGraph(State)
graph.add_node("classify", classify)
for kind in ("check", "write", "other"):
    graph.add_node(kind, lambda state: {"answer": act(state["route"])})
graph.add_edge(START, "classify")
graph.add_conditional_edges("classify", lambda state: state["route"].kind)
for kind in ("check", "write", "other"):
    graph.add_edge(kind, END)
app = graph.compile()

def langgraph(request):
    state = app.invoke({"request": request})
    return state["route"], state["usage"]


for name, way in (("our code", ours), ("Pydantic AI", pydantic_ai), ("LangGraph", langgraph)):
    start, cost, tokens, kinds = time.perf_counter(), 0.0, 0, []
    for request in REQUESTS:
        route, used = way(request)
        cost, tokens = cost + usage.cost(prices, cfg.model, used), tokens + used.input_tokens
        kinds.append(route.kind)
        if name == "our code":
            print(f"  {route.kind:5} -> {act(route)[:70]}")
    print(f"{name:12} routes: {', '.join(kinds)}; {tokens:,} input tokens, ${cost:.4f}, {time.perf_counter() - start:4.1f} s\n")
