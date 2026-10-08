import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-haiku-4-5"
messages = [{"role": "user", "content": "Write one quiz question about HTTP status codes, with four options and the answer."}]
partial = ""

try:
    with client.messages.stream(model=MODEL, max_tokens=300, messages=messages) as stream:
        for i, text in enumerate(stream.text_stream):
            partial += text
            print(text, end="", flush=True)
            if i == 12:
                raise ConnectionError("the network dropped")   # a stand-in for a real drop
except ConnectionError as error:
    print(f"\n--- stream broke: {error}; kept {len(partial)} characters ---")

# Claude 4.5 and earlier: send the partial reply back as the start of the assistant turn
messages.append({"role": "assistant", "content": partial.rstrip()})
with client.messages.stream(model=MODEL, max_tokens=300, messages=messages) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
    message = stream.get_final_message()
print(f"\n--- resumed: {message.stop_reason}, {message.usage.output_tokens} more tokens ---")
