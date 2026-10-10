import base64
import math

import anthropic
from dotenv import load_dotenv

from quizforge.tools import cfg

load_dotenv()
client = anthropic.Anthropic()
SLIDE = cfg.library.parent / "v1-docs" / "L3.2-slide.png"  # 1920 x 1080

data = base64.standard_b64encode(SLIDE.read_bytes()).decode()
source = {"type": "base64", "media_type": "image/png", "data": data}
image = {"type": "image", "source": source}
ask = {
    "type": "text",
    "text": "This slide is from a lesson. Write one question it "
    "answers: four short options, then the key. Plain text, no Markdown.",
}

text_only = client.messages.count_tokens(model=cfg.model, messages=[{"role": "user", "content": [ask]}])
reply = client.messages.create(
    model=cfg.model, max_tokens=300, messages=[{"role": "user", "content": [image, ask]}]
)  # the image first
print(reply.content[0].text)

# Haiku 4.5 scales 1920 x 1080 to 1456 x 819; a 28 x 28 patch is one token
print("expected:", math.ceil(1456 / 28) * math.ceil(819 / 28), "image tokens")
print("measured:", reply.usage.input_tokens - text_only.input_tokens, "image tokens")
