import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-haiku-5-5"   # mid-conversation system messages need a newer model
SYSTEM = open("prompts/item_writer/system.md").read()
lesson = open("library/ccao-f/v1/L2.1.md").read()
first = f'<lesson id="L2.1">\n{lesson}\n</lesson>\n\nWrite 1 question.'
chat = [{"role": "user", "content": first}]


def send(system, messages, label):
    message = client.messages.create(model=MODEL, max_tokens=3000, system=system,
                                     messages=messages, output_config={"effort": "low"},
                                     cache_control={"type": "ephemeral"})
    u = message.usage
    print(f"{label:20} cache read {u.cache_read_input_tokens:5}   "
          f"cache write {u.cache_creation_input_tokens:5}   new input {u.input_tokens}")
    return "".join(block.text for block in message.content if block.type == "text")


chat += [{"role": "assistant", "content": send(SYSTEM, chat, "turn 1")},
         {"role": "user", "content": "One more."}]
chat += [{"role": "assistant", "content": send(SYSTEM, chat, "turn 2")},
         {"role": "user", "content": "One more."}]
HARD = "From now on, make every question hard: two options that both look right."
send(SYSTEM + "\n\n" + HARD, chat, "A: edit the system")
send(SYSTEM, chat + [{"role": "system", "content": HARD}], "B: system message")
