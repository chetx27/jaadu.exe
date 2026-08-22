from __future__ import annotations

import pandas as pd
from jaadu.ingestion.documents import documents_as_of
from jaadu.validation.checks import as_of_panel


def audit_observations(observations: pd.DataFrame, cutoff: str) -> dict:
    obs = observations.copy()
    obs["timestamp"] = pd.to_datetime(obs["timestamp"])
    obs["available_at"] = pd.to_datetime(obs["available_at"])
    cut = pd.Timestamp(cutoff)
    used = as_of_panel(obs, cutoff)
    leaked_avail = int((used["available_at"] > cut).sum())
    avail_before_valid = int((obs["available_at"] < obs["timestamp"]).sum())
    future_valid_in_used = int((used["timestamp"] > cut).sum())
    return {
        "cutoff": cutoff,
        "n_raw": int(len(obs)),
        "n_used": int(len(used)),
        "leaked_available_at_after_cutoff": leaked_avail,
        "available_at_before_valid_time": avail_before_valid,
        "future_valid_time_in_used": future_valid_in_used,
        "pass": leaked_avail == 0 and future_valid_in_used == 0 and avail_before_valid == 0,
        "caveat": "ERA5/GloFAS are retrospective reanalyses. Passing this audit does not make the replay operationally real-time.",
    }


def audit_documents(cutoff: str) -> dict:
    admitted = documents_as_of(cutoff)
    cut = pd.Timestamp(cutoff)
    leaked = [d["doc_id"] for d in admitted if pd.Timestamp(d["published_at"]) > cut]
    return {
        "cutoff": cutoff,
        "n_admitted": len(admitted),
        "leaked_doc_ids": leaked,
        "pass": len(leaked) == 0,
        "admitted_ids": [d["doc_id"] for d in admitted],
    }


def audit_investigation_payload(payload: dict, cutoff: str) -> dict:
    cut = pd.Timestamp(cutoff)
    issues = []
    for e in payload.get("evidence", []):
        if pd.Timestamp(e.get("published_at", cutoff)) > cut:
            issues.append({"type": "document", "id": e.get("evidence_id")})
    for t in payload.get("panel_index", []):
        if pd.Timestamp(t) > cut:
            issues.append({"type": "panel_timestamp", "id": t})
    g = payload.get("graph") or {}
    if g.get("as_of") and pd.Timestamp(g["as_of"]) > cut:
        issues.append({"type": "graph_as_of", "id": g["as_of"]})
    return {
        "cutoff": cutoff,
        "n_issues": len(issues),
        "issues": issues,
        "pass": len(issues) == 0,
    }


def run_leakage_audit(observations: pd.DataFrame, cutoff: str, payload: dict | None = None) -> dict:
    obs_audit = audit_observations(observations, cutoff)
    doc_audit = audit_documents(cutoff)
    inv_audit = audit_investigation_payload(payload, cutoff) if payload else {"pass": True, "n_issues": 0}
    return {
        "observations": obs_audit,
        "documents": doc_audit,
        "investigation": inv_audit,
        "pass": bool(obs_audit["pass"] and doc_audit["pass"] and inv_audit.get("pass", True)),
    }
