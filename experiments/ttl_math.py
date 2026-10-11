"""The 5-minute or the 1-hour cache? The same prefix used 4 times, with a gap between uses, priced on Claude
Haiku 4.5 (no requests: arithmetic from pricing.toml). Writes cost 1.25x (5 minutes) or 2x (1 hour) the input
price, reads 0.1x; a read refreshes the entry; an entry older than its TTL is gone and is written again."""
from quizforge import usage
from quizforge.config import ROOT

P = usage.load_prices(ROOT / "pricing.toml")["claude-haiku-4-5-20251001"]
PREFIX, USES = 6_340, 4  # L2.4's cached prefix, from the cache lab


def dollars(gap_minutes, write, ttl):
    """Cost of USES uses of the prefix: the first one writes; each later one reads if the entry is still alive."""
    alive = gap_minutes < ttl
    times = write + (USES - 1) * (P["cache_read"] if alive else write)
    return PREFIX * times * P["input"] / 1_000_000


print(f"{USES} uses of a {PREFIX:,}-token prefix        no cache    5-minute    1-hour")
for gap in (2, 10, 30, 90):
    none = USES * PREFIX * P["input"] / 1_000_000
    five, hour = dollars(gap, P["cache_write"], 5), dollars(gap, P["cache_write_1h"], 60)
    best = min((none, "no cache"), (five, "5-minute"), (hour, "1-hour"))[1]
    print(f"  {gap:3} minutes between uses       ${none:.5f}   ${five:.5f}   ${hour:.5f}   cheapest: {best}")
