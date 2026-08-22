from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from jaadu.core.config import DATA


def evidence_dir() -> Path:
    p = DATA / "evidence"
    p.mkdir(parents=True, exist_ok=True)
    return p


def provenance_hash(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return sha256(blob).hexdigest()[:16]


def append_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for rec in records:
            f.write(json.dumps(rec, default=str) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out
