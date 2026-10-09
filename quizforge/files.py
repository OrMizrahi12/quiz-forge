"""Upload a file once with the Files API, then reuse its file_id."""
import hashlib
import json
import mimetypes
from pathlib import Path

import anthropic

from quizforge.config import ROOT

INDEX = ROOT / "runs" / "files.json"   # sha256 of the file -> file_id


def file_id(client, path) -> tuple[str, bool]:
    """The file_id for this file, and whether it was uploaded just now."""
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    index = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    if digest in index:
        try:
            client.files.retrieve_metadata(index[digest])   # still there?
            return index[digest], False
        except anthropic.NotFoundError:
            pass                                 # deleted or expired: upload again
    media_type = mimetypes.guess_type(path.name)[0]
    uploaded = client.files.upload(file=(path.name, path.read_bytes(), media_type))
    index[digest] = uploaded.id
    INDEX.parent.mkdir(exist_ok=True)
    INDEX.write_text(json.dumps(index, indent=1))
    return uploaded.id, True
