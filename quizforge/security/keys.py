"""Where the correct answer sits is decided by code, not by the model: a hidden instruction can't put every key at A.
The four options are shuffled with a seed, so the same lesson always gets the same order."""

import random


def place(data, seed):
    """Shuffle each question's options and move its answer letter with them. data: a Questions object."""
    rng = random.Random(seed)
    for q in data.questions:
        right = getattr(q, q.answer.lower())
        options = [q.a, q.b, q.c, q.d]
        rng.shuffle(options)
        q.a, q.b, q.c, q.d = options
        q.answer = "ABCD"[options.index(right)]
    return data
