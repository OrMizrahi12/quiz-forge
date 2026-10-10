"""Find the passages that answer a question: the library split into sections, scored by shared words, sent as search results."""

import math
import re
from collections import Counter

from quizforge.library import lesson_ids, load_lesson

WORD = re.compile(r"[a-z0-9]+")
COMMON = set(
    "the a an and or of to in on for is are be it this that with as by at from what when how which you your".split()
)


def words(text):
    """Lowercase words without the most common ones; a plural counts as its singular."""
    return [
        w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
        for w in WORD.findall(text.lower())
        if w not in COMMON
    ]


def chunks(library):
    """One chunk per lesson section (## heading): small enough to send a few, big enough to make sense alone."""
    out = []
    for lesson in lesson_ids(library):
        text = load_lesson(library, lesson)
        title = text.splitlines()[0].lstrip("# ")
        for part in re.split(r"\n(?=## )", text)[1:]:
            heading, _, body = part.partition("\n")
            if heading.startswith(("## Chapters", "## Sources")):
                continue  # timestamps and links: nothing to answer from
            out.append(
                {
                    "source": f"{lesson}#{heading.lstrip('# ').lower().replace(' ', '-')}",
                    "title": f"{title}  {heading.lstrip('# ')}",
                    "text": body.strip(),
                }
            )
    return out


def search(library, query, k=3):
    """The k sections that best match the query: BM25, a keyword score that favors rare words and short sections (no embeddings)."""
    found = chunks(library)
    bags = [Counter(words(c["text"])) for c in found]
    avg = sum(sum(b.values()) for b in bags) / len(bags)
    df = Counter(w for b in bags for w in b)

    def score(bag):
        size = sum(bag.values())
        return sum(
            math.log(1 + (len(bags) - df[w] + 0.5) / (df[w] + 0.5))
            * bag[w]
            * 2.2
            / (bag[w] + 1.2 * (0.25 + 0.75 * size / avg))
            for w in set(words(query))
            if w in bag
        )

    ranked = sorted(range(len(found)), key=lambda i: score(bags[i]), reverse=True)
    return [found[i] for i in ranked[:k]]


def as_results(found):
    """Search result blocks: Claude cites them like web results, with our source and title."""
    return [
        {
            "type": "search_result",
            "source": c["source"],
            "title": c["title"],
            "content": [{"type": "text", "text": c["text"]}],
            "citations": {"enabled": True},
        }
        for c in found
    ]
