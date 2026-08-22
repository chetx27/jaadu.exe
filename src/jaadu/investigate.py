from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
from jaadu.anomaly.detect import detect
from jaadu.core.config import DATA, engine_config, region_by_id
from jaadu.core.registry import load_registry, processed_path
from jaadu.core.schemas import Availability, AlertReport
from jaadu.counterfactuals.scenarios import expected_pattern, matched_driver_hold
from jaadu.graph.temporal import anomalous_subgraph, build_graph, node_type_for
from jaadu.hypotheses.engine import challenge, instantiate_hypotheses
from jaadu.multimodal.extract import extract_corpus
from jaadu.validation.checks import pivot_region
from jaadu.voi.rank import rank_observations


def load_observations() -> pd.DataFrame:
    path = processed_path("observations.parquet")
    if not path.exists():
        raise FileNotFoundError("Run `python -m jaadu ingest` first.")
    return pd.read_parquet(path)


def world_state(geo_id: str, as_of: str) -> dict:
    obs = load_observations()
    panel = pivot_region(obs, geo_id, as_of)
    registry = {r.dataset_id: r.model_dump() for r in load_registry()}
    unavailable = [r.model_dump() for r in load_registry() if r.status == Availability.UNAVAILABLE]
    return {
        "geo_id": geo_id,
        "as_of": as_of,
        "n_timestamps": int(len(panel)),
        "variables": list(panel.columns),
        "unavailable_datasets": unavailable,
        "registry": registry,
        "panel_tail": panel.tail(18)
        .reset_index()
        .assign(timestamp=lambda d: d["timestamp"].astype(str))
        .to_dict(orient="records")
        if not panel.empty
        else [],
    }


def investigate(geo_id: str, as_of: str, use_gemini: bool | None = None) -> dict:
    cfg = engine_config()
    obs = load_observations()
    panel = pivot_region(obs, geo_id, as_of)
    if panel.empty:
        return {"error": "no_data", "geo_id": geo_id, "as_of": as_of}
    detection = detect(panel, as_of)
    z = detection.pop("seasonal_z")
    z_tail = z.tail(24)
    graph = build_graph(panel, geo_id, as_of)
    evidence = extract_corpus(as_of, use_gemini=use_gemini)
    hyps = instantiate_hypotheses(geo_id, as_of, detection, graph, evidence)
    leading = hyps[0]
    challenged = challenge(leading, hyps[1:], detection)
    cf = {
        h.template_id: {
            "expected": expected_pattern(h.template_id, detection),
            "matched": matched_driver_hold(
                panel,
                as_of,
                h.template_id,
                [
                    s["variable"]
                    for s in detection["current_signals"]
                    if node_type_for(s["variable"]).value != "CLIMATE"
                ][:4],
            ),
        }
        for h in hyps[:4]
    }
    already = set(panel.columns)
    voi = rank_observations(hyps, already_have=already)
    pathway = anomalous_subgraph(graph, detection, cfg["anomaly"]["robust_z_threshold"])
    voi0 = voi[0] if voi else None
    posterior = leading.score.posterior
    if posterior >= cfg["voi"]["decision_threshold"] and detection["multi_signal_alert"]:
        action_kind = "low_regret"
        low_regret = "Issue an investigation bulletin and pre-position monitoring; do not trigger a costly intervention on this evidence alone."
    elif detection["multi_signal_alert"]:
        action_kind = "investigation"
        low_regret = f"Collect '{(voi0.label if voi0 else 'additional independent evidence')}' before any intervention."
    else:
        action_kind = "investigation"
        low_regret = "Continue monitoring; joint anomaly does not meet the multi-signal rule."
    report = AlertReport(
        alert_id=f"{geo_id}:{as_of}",
        risk="emerging multi-domain anomaly"
        if detection["multi_signal_alert"]
        else "no multi-signal alert",
        geography=geo_id,
        detection_time=as_of,
        earliest_signal=detection.get("earliest_signal"),
        current_signals=detection["current_signals"],
        discovered_pathway=pathway,
        leading_hypothesis=leading,
        alternatives=hyps[1:4],
        confidence={
            "data_quality": "moderate" if panel.shape[1] >= 6 else "low",
            "detection_confidence": "moderate" if detection["multi_signal_alert"] else "low",
            "causal_confidence": "low",
            "historical_precedent": "moderate"
            if detection["combination"].get("historical_count", 0)
            else "low",
            "recommended_action_confidence": "moderate" if action_kind != "intervention" else "low",
            "meaning": "These are qualitative calibrations of separate uncertainty types, not a single 0-100 score. Causal confidence stays low because edges are observational.",
        },
        expected_development="If the leading pathway continues, agricultural and then market stress would be expected to become visible in slower official statistics after the cutoff.",
        what_would_invalidate=challenged["attacks"]
        + [
            "A second rainfall dataset showing no deficit.",
            "Local market prices remaining at seasonal baseline while only reanalysis moved.",
        ],
        next_best_observation=voi0,
        low_regret_action=low_regret,
        intervention_vs_investigation=action_kind,
        data_sources=sorted({str(s) for s in obs["source"].dropna().unique()}),
        provenance_ids=[e["evidence_id"] for e in evidence]
        + [s.get("variable", "") for s in detection["current_signals"]],
    )
    result = {
        "region": region_by_id(geo_id),
        "as_of": as_of,
        "world_state_summary": {
            "n_variables": int(panel.shape[1]),
            "n_months": int(panel.shape[0]),
            "unavailable": [
                r.dataset_id for r in load_registry() if r.status.value == "unavailable"
            ],
        },
        "detection": detection,
        "z_tail": z_tail.reset_index()
        .assign(timestamp=lambda d: d["timestamp"].astype(str))
        .to_dict(orient="records"),
        "graph": graph,
        "hypotheses": [h.model_dump() for h in hyps],
        "challenge": challenged,
        "counterfactuals": cf,
        "voi": [v.model_dump() for v in voi],
        "report": report.model_dump(),
        "evidence": evidence,
        "panel_index": [t.isoformat() for t in panel.index],
    }
    out = DATA / "processed" / f"investigation_{geo_id}_{as_of}.json"
    out.write_text(json.dumps(result, indent=2, default=str))
    return result


def perturb(geo_id: str, as_of: str, variable: str, delta_z: float) -> dict:
    obs = load_observations()
    panel = pivot_region(obs, geo_id, as_of)
    if variable not in panel.columns:
        return {"error": f"{variable} not in panel"}
    panel = panel.copy()
    last = panel.index[-1]
    panel.loc[last, variable] = panel.loc[last, variable] + delta_z * (panel[variable].std() or 1)
    detection = detect(panel, as_of)
    detection.pop("seasonal_z")
    graph = build_graph(panel, geo_id, as_of)
    hyps = instantiate_hypotheses(geo_id, as_of, detection, graph, [])
    return {
        "note": "Synthetic perturbation of the last available month. Not an observation.",
        "variable": variable,
        "delta_z": delta_z,
        "detection": detection,
        "hypotheses": [h.model_dump() for h in hyps[:5]],
        "pathway": anomalous_subgraph(graph, detection),
        "graph": graph,
    }


def ablate(geo_id: str, as_of: str, drop_variables: list[str]) -> dict:
    obs = load_observations()
    panel = pivot_region(obs, geo_id, as_of)
    panel = panel.drop(columns=[c for c in drop_variables if c in panel.columns], errors="ignore")
    detection = detect(panel, as_of)
    detection.pop("seasonal_z")
    graph = build_graph(panel, geo_id, as_of)
    hyps = instantiate_hypotheses(geo_id, as_of, detection, graph, [])
    voi = rank_observations(hyps, already_have=set(panel.columns))
    return {
        "dropped": drop_variables,
        "remaining": list(panel.columns),
        "detection": detection,
        "hypotheses": [h.model_dump() for h in hyps[:5]],
        "voi": [v.model_dump() for v in voi[:5]],
        "note": "Variables were removed, not imputed.",
    }
