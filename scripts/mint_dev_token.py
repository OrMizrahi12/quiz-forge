"""A new development token for the library server. The token goes to a file only you can read;
the server keeps only its hash. Nothing secret is printed."""
import secrets
from pathlib import Path

from mcp_server.auth import HASHES, digest

TOKEN = Path.home() / ".config/quiz-forge/mcp-token"

TOKEN.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
token = secrets.token_urlsafe(32)
for path, text in ((TOKEN, token), (HASHES, digest(token))):  # a new token replaces the old one
    path.touch(mode=0o600)
    path.write_text(text + "\n")
print(f"dev token written to {TOKEN} (mode 600); its hash is registered")
