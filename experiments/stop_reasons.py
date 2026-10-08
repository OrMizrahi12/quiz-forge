import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
PROMPT = "Write one quiz question about HTTP status codes, with four options."
SAVE = {
    "name": "save_question",
    "description": "Save a finished quiz question to the bank.",
    "input_schema": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]},
}


def handle(message):
    match message.stop_reason:
        case "end_turn":
            return "finished: use the text"
        case "stop_sequence":
            return f"stopped at {message.stop_sequence!r}: use the text"
        case "max_tokens" | "model_context_window_exceeded":
            return "truncated: raise max_tokens or continue, never save it as complete"
        case "tool_use":
            return "run the tool, then send back a tool_result"
        case "pause_turn":
            return "send the content back, so Claude can continue"
        case "refusal":
            return f"declined ({message.stop_details}): try a fallback model"
        case _:
            return "unknown: log the request id"


def ask(label, **options):
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=options.pop("max_tokens", 200),
        messages=[{"role": "user", "content": PROMPT}],
        **options,
    )
    print(f"--- {label}: {message.stop_reason}, {message.usage.input_tokens} in, {message.usage.output_tokens} out")
    print("   ", handle(message))
    last = message.content[-1]
    print("   ", last.input if last.type == "tool_use" else repr(last.text[-40:]))


ask("plain")
ask("tiny cap", max_tokens=15)
ask("stop sequence", stop_sequences=["B)"])
ask("tool", tools=[SAVE], tool_choice={"type": "tool", "name": "save_question"})
