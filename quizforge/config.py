import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    model: str
    library: Path
    max_tokens: int
    max_request_usd: float
    concurrency: int
    questions: int
    usage_log: Path
    output_dir: Path


def load_config(path=ROOT / "config.toml"):
    data = tomllib.loads(Path(path).read_text())
    return Config(
        model=data["model"]["writer"],
        library=ROOT / data["library"]["path"],
        max_tokens=data["limits"]["max_tokens"],
        max_request_usd=data["limits"]["max_request_usd"],
        concurrency=data["limits"]["concurrency"],
        questions=data["generate"]["questions"],
        usage_log=ROOT / data["generate"]["usage_log"],
        output_dir=ROOT / data["generate"]["output_dir"],
    )
