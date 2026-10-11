"""The same job failing in two different layers, traced. Usage: python -m experiments.two_layers integration|output
integration: the API is overloaded (our local mock answers 529, with a dummy key).
output: the call works, but the reply is cut off (max_tokens set to 300 on purpose; one real request)."""
import sys
from dataclasses import replace

import anthropic

from experiments.mock_api import serve
from quizforge import tracing, usage
from quizforge.config import ROOT, load_config
from quizforge.generate import generate_one

cfg, prices = load_config(), usage.load_prices(ROOT / "pricing.toml")
path = tracing.setup()
if sys.argv[1] == "integration":
    serve(["529"])
    mock = anthropic.Anthropic(base_url="http://127.0.0.1:8787", api_key="mock-not-a-real-key", max_retries=2,
                               middleware=[tracing.http_span])
    result = generate_one(cfg, prices, "L2.1", client=mock, out=lambda line: None)
else:
    result = generate_one(replace(cfg, max_tokens=300), prices, "L2.1", out=lambda line: None)
print(f"L2.1: {result['status']}, {result['problems'][0]} -> {path.relative_to(ROOT)}")
