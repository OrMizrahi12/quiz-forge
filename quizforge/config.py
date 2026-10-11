import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    model: str
    library: Path
    prompts: Path
    prompt: str
    max_tokens: int
    max_request_usd: float
    concurrency: int
    questions: int
    retries: int
    usage_log: Path
    output_dir: Path
    rejected_dir: Path
    rounds: int
    max_turns: int
    max_usd: float
    bank: Path
    similar: float
    ask_turns: int
    ask_usd: float


def load_config(path=ROOT / "config.toml"):
    data = tomllib.loads(Path(path).read_text())
    return Config(
        model=data["model"]["writer"],
        library=ROOT / data["library"]["path"],
        prompts=ROOT / data["prompt"]["folder"],
        prompt=data["prompt"]["item_writer"],
        max_tokens=data["limits"]["max_tokens"],
        max_request_usd=data["limits"]["max_request_usd"],
        concurrency=data["limits"]["concurrency"],
        questions=data["generate"]["questions"],
        retries=data["generate"]["retries"],
        usage_log=ROOT / data["generate"]["usage_log"],
        output_dir=ROOT / data["generate"]["output_dir"],
        rejected_dir=ROOT / data["generate"]["rejected_dir"],
        rounds=data["write"]["rounds"],
        max_turns=data["write"]["max_turns"],
        max_usd=data["write"]["max_usd"],
        bank=ROOT / data["bank"]["path"],
        similar=data["bank"]["similar"],
        ask_turns=data["ask"]["max_turns"],
        ask_usd=data["ask"]["max_usd"],
    )
