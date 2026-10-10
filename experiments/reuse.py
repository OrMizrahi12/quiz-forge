import base64
import json

import anthropic
from dotenv import load_dotenv

from quizforge.files import file_id
from quizforge.tools import cfg

load_dotenv()
client = anthropic.Anthropic()
PDF = cfg.library.parent / "v1-docs" / "L3.2.pdf"

fid, new = file_id(client, PDF)
print("uploaded" if new else "reused", fid)
inline = {
    "type": "base64",
    "media_type": "application/pdf",
    "data": base64.standard_b64encode(PDF.read_bytes()).decode(),
}
by_id = {"type": "file", "file_id": fid}
for source in (inline, by_id):
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "document", "source": source},
                {"type": "text", "text": "In one sentence: what is a hallucination?"},
            ],
        }
    ]
    reply = client.messages.create(model=cfg.model, max_tokens=200, messages=messages)
    size = len(json.dumps(messages))
    print(f"{source['type']}: {size:,} bytes sent, {reply.usage.input_tokens} in")
