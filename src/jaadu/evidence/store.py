from __future__ import annotations

import json
from pathlib import Path
from jaadu.core.provenance import evidence_dir, read_jsonl


def evidence_index() -> dict[str, dict]:
    idx = {}
    root = evidence_dir()
    for path in sorted(root.glob("evidence_*.json")):
        payload = json.loads(path.read_text())
        if isinstance(payload, list):
            for rec in payload:
                if rec.get("evidence_id"):
                    idx[rec["evidence_id"]] = rec
    for path in sorted(root.glob("*.jsonl")):
        for rec in read_jsonl(path):
            eid = rec.get("evidence_id") or rec.get("doc_id")
            if eid:
                idx[str(eid)] = rec
    return idx


def get_evidence(evidence_id: str) -> dict | None:
    return evidence_index().get(evidence_id)


def trace_conclusion(provenance_ids: list[str], observations: list[dict] | None = None) -> dict:
    idx = evidence_index()
    docs = []
    missing = []
    for pid in provenance_ids:
        if pid in idx:
            rec = idx[pid]
            docs.append(
                {
                    "id": pid,
                    "source": rec.get("source"),
                    "published_at": rec.get("published_at"),
                    "geographic_scope": rec.get("geographic_scope"),
                    "claim": rec.get("claim"),
                    "supporting_passage": rec.get("supporting_passage"),
                    "extraction_kind": rec.get("extraction_kind"),
                }
            )
        else:
            missing.append(pid)
    obs_hits = []
    if observations:
        by_id = {str(r.get("observation_id") or r.get("variable")): r for r in observations}
        for pid in provenance_ids:
            if pid in by_id:
                obs_hits.append(by_id[pid])
    return {
        "documents": docs,
        "observations": obs_hits,
        "unresolved_ids": missing,
    }


def write_bundle(name: str, records: list[dict]) -> Path:
    path = evidence_dir() / name
    path.write_text(json.dumps(records, indent=2, default=str))
    return path
