"""FR-2: the exam blueprint drives the plan. blueprint.toml gives each domain its weight and the library's lessons that
teach it; plan() splits n items over the domains this library covers, in proportion to their weights (largest
remainder, so the total is exactly n), then over each domain's lessons in order. Domains with no lessons are a
coverage gap: reported with their weight, never silently given items.
Usage: python -m quizforge plan --n 20"""

import json
import tomllib
from pathlib import Path

from quizforge.config import ROOT

BLUEPRINT = "blueprint.toml"


class BlueprintError(ValueError):
    pass


def load(path=ROOT / BLUEPRINT, library=None):
    """The blueprint's domains as [(name, weight, [lessons])], checked against the library's MANIFEST.json."""
    path = Path(path)
    if not path.exists():
        raise BlueprintError(f"no {path.name} in {path.parent}: qf init writes one; see the README")
    domains = [
        (d["name"], float(d["weight"]), list(d.get("lessons", []))) for d in tomllib.loads(path.read_text())["domain"]
    ]
    total = sum(weight for _, weight, _ in domains)
    if abs(total - 100) > 0.5:
        raise BlueprintError(f"the weights add up to {total:g}, not 100")
    seen = {}
    for name, _, lessons in domains:
        for lesson in lessons:
            if lesson in seen:
                raise BlueprintError(f"{lesson} is in two domains: {seen[lesson]} and {name}")
            seen[lesson] = name
    if library is not None:
        known = {row["lesson"] for row in json.loads((Path(library) / "MANIFEST.json").read_text())["lessons"]}
        unknown = sorted(set(seen) - known)
        if unknown:
            raise BlueprintError(f"not in the library: {', '.join(unknown)}")
    return domains


def domain_of(domains):
    """lesson id -> domain name, for the lessons the blueprint maps."""
    return {lesson: name for name, _, lessons in domains for lesson in lessons}


def split(weights, n):
    """Largest remainder: whole parts first, then the leftover items to the largest fractions (ties: listed order)."""
    total = sum(weights)
    shares = [n * w / total for w in weights]
    counts = [int(s) for s in shares]
    order = sorted(range(len(weights)), key=lambda i: (-(shares[i] - counts[i]), i))
    for i in order[: n - sum(counts)]:
        counts[i] += 1
    return counts


def plan(domains, n):
    """(rows, gaps): rows = [(domain, lesson, items)] summing to n; gaps = [(domain, weight)] the library doesn't teach."""
    covered = [(name, weight, lessons) for name, weight, lessons in domains if lessons]
    gaps = [(name, weight) for name, weight, lessons in domains if not lessons]
    if n < len(covered):
        raise BlueprintError(f"n = {n} is fewer than the {len(covered)} domains the library covers")
    rows = []
    for (name, _, lessons), count in zip(covered, split([w for _, w, _ in covered], n)):
        rows += [(name, lesson, k) for lesson, k in zip(lessons, split([1] * len(lessons), count)) if k]
    return rows, gaps


def show(rows, gaps, n):
    lines = [f"{'domain':44}{'lesson':>8}{'items':>7}"]
    lines += [f"{name:44}{lesson:>8}{k:>7}" for name, lesson, k in rows]
    lines.append(f"{'total':44}{'':>8}{n:>7}")
    if gaps:
        share = sum(weight for _, weight in gaps)
        lines.append(
            f"not covered by this library ({share:g}% of the blueprint): "
            + ", ".join(f"{name} {weight:g}%" for name, weight in gaps)
        )
    return lines
