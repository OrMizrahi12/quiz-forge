"""Evidence for a reviewer: the lesson's PDF, uploaded once, and Claude's answer with citations that point to its pages."""

from quizforge.files import file_id

ASK = (
    "For each practice question below, find the passage of the lesson that supports the answer marked correct. "
    "Answer in one short sentence per question, starting with 'Question <n>:'."
)


def pdf_of(cfg, lesson_id):
    path = cfg.library.parent / f"{cfg.library.name}-docs" / f"{lesson_id}.pdf"
    if not path.exists():
        raise FileNotFoundError(f"no PDF for {lesson_id} in {path.parent.name}/")
    return path


def evidence(client, cfg, lesson_id, questions):
    """Returns (claims, usage, uploaded): each claim's text with its cited passages and pages.

    The PDF goes up once with the Files API; later calls send only its file_id. Citations are on, so every
    cited_text is the document's own words, with the page it's on. (Citations and structured outputs can't
    be combined: the reply is text.)
    """
    fid, uploaded = file_id(client, pdf_of(cfg, lesson_id))
    shown = "\n".join(
        f"Question {n}: {q['scenario']} Correct: {q['answer']}) {q[q['answer'].lower()]}"
        for n, q in enumerate(questions, 1)
    )
    document = {
        "type": "document",
        "source": {"type": "file", "file_id": fid},
        "title": f"Lesson {lesson_id}",
        "citations": {"enabled": True},
    }
    reply = client.messages.create(
        model=cfg.model,
        max_tokens=700,
        messages=[{"role": "user", "content": [document, {"type": "text", "text": f"{ASK}\n\n{shown}"}]}],
    )
    claims = []
    for block in reply.content:
        if block.type != "text":
            continue
        cites = [
            (c.cited_text.strip(), c.start_page_number) for c in (block.citations or []) if c.type == "page_location"
        ]
        if cites or block.text.strip():
            claims.append({"text": block.text.strip(), "citations": cites})
    return claims, reply.usage, uploaded
