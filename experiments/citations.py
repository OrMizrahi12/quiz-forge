import base64

import anthropic
from dotenv import load_dotenv

from quizforge.library import load_lesson
from quizforge.tools import cfg

load_dotenv()
client = anthropic.Anthropic()
notes = load_lesson(cfg.library, "L3.2")
pdf = (cfg.library.parent / "v1-docs" / "L3.2.pdf").read_bytes()
SOURCES = {
    "text": {"type": "text", "media_type": "text/plain", "data": notes},
    "pdf": {"type": "base64", "media_type": "application/pdf",
            "data": base64.standard_b64encode(pdf).decode()},
}
ASK = ("Where does fabrication concentrate, and how do you set up "
       "a request so a gap gets admitted?")

for kind, source in SOURCES.items():
    document = {"type": "document", "source": source,
                "title": "Lesson 3.2: Hallucinations", "citations": {"enabled": True}}
    reply = client.messages.create(model=cfg.model, max_tokens=600, messages=[
        {"role": "user", "content": [document, {"type": "text", "text": ASK}]}])
    usage = reply.usage
    print(f"--- as {kind}: {usage.input_tokens} in, {usage.output_tokens} out")
    for block in reply.content:
        if block.citations:
            print(f"  {block.text.strip()[:72]!r}")
        for cite in block.citations or []:
            if cite.type == "char_location":   # text: character offsets
                start, end = cite.start_char_index, cite.end_char_index
                same = notes[start:end] == cite.cited_text
                where = f"chars {start}-{end}, " + ("matches" if same else "NO MATCH")
            else:                              # PDF: page numbers, from 1
                where = f"page {cite.start_page_number}"
            print(f"    [{where}] {cite.cited_text.strip()[:46]!r}")
