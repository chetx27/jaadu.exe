from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
from jaadu.anomaly.detect import detect
from jaadu.baselines.methods import run_baselines
from jaadu.core.config import EXPERIMENTS, load_benchmark, load_registry
from jaadu.core.registry import processed_path
from jaadu.graph.temporal import build_graph, node_type_for
from jaadu.hypotheses.engine import instantiate_hypotheses
from jaadu.investigate import investigate
from jaadu.validation.checks import pivot_region
from jaadu.voi.rank import rank_observations


def _obs() -> pd.DataFrame:
    return pd.read_parquet(processed_path("observations.parquet"))


def scan_months(start: str, end: str) -> list[pd.Timestamp]:
    return list(pd.date_range(start, end, freq="MS"))


def evaluate_event(event: dict, observations: pd.DataFrame) -> dict:
    geo = event["region"]
    cutoff = event["prediction_cutoff"]
    panel = pivot_region(observations, geo, cutoff)
    inv = investigate(geo, cutoff, use_gemini=False)
    detection = inv["detection"]
    hyps = inv["hypotheses"]
    leading = hyps[0] if hyps else {}
    mechanism = event["documented_mechanism_template"]
    hypothesis_hit = leading.get("template_id") == mechanism
    first_detect = None
    false_alarms = 0
    for t in scan_months(event["event_window_start"], cutoff):
        p = pivot_region(observations, geo, t.strftime("%Y-%m-%d"))
        if p.empty:
            continue
        d = detect(p, t.strftime("%Y-%m-%d"))
        if d["multi_signal_alert"] and first_detect is None:
            first_detect = t
    for a, b in event.get("negative_control_windows", []):
        for t in scan_months(a, b):
            p = pivot_region(observations, geo, t.strftime("%Y-%m-%d"))
            if p.empty:
                continue
            d = detect(p, t.strftime("%Y-%m-%d"))
            if d["multi_signal_alert"]:
                false_alarms += 1
    conventional = pd.Timestamp(event["conventional_visible_date"])
    lead_days = None
    if first_detect is not None:
        lead_days = int((conventional - first_detect).days)
    baselines = run_baselines(panel, cutoff, geo)
    pathway = inv["report"]["discovered_pathway"]
    discovered_unspecified = False
    for e in inv["graph"]["edges"]:
        st = node_type_for(e["source"]).value
        tt = node_type_for(e["target"]).value
        if st in {"CLIMATE", "WATER"} and tt in {"AGRICULTURE", "WATER", "MARKET"}:
            discovered_unspecified = True
            break
    voi = inv["voi"]
    voi_quality = None
    if voi:
        top_vars = [v["variable"] for v in voi[:3]]
        voi_quality = {
            "top3": top_vars,
            "reservoir_or_ndvi_in_top3": any(
                (v in top_vars for v in ("reservoir_storage", "ndvi"))
            ),
        }
    return {
        "event_id": event["id"],
        "cutoff": cutoff,
        "multi_signal_alert_at_cutoff": detection["multi_signal_alert"],
        "conventional_univariate_hit_at_cutoff": detection["conventional_univariate_hit"],
        "n_abnormal": detection["n_abnormal"],
        "earliest_signal": detection.get("earliest_signal"),
        "first_multi_signal_in_window": None
        if first_detect is None
        else first_detect.strftime("%Y-%m-%d"),
        "lead_days_vs_conventional": lead_days,
        "leading_hypothesis": leading.get("template_id"),
        "leading_posterior": leading.get("score", {}).get("posterior"),
        "hypothesis_matches_documented": hypothesis_hit,
        "false_alarms_in_negative_windows": false_alarms,
        "baselines_at_cutoff": baselines,
        "discovered_cross_domain_edge": discovered_unspecified,
        "pathway": pathway,
        "voi": voi_quality,
        "challenge": inv["challenge"],
        "confidence": inv["report"]["confidence"],
    }


def ablations(event: dict, observations: pd.DataFrame) -> dict:
    geo = event["region"]
    cutoff = event["prediction_cutoff"]
    panel = pivot_region(observations, geo, cutoff)
    variants = {
        "full": panel,
        "no_climate": panel.drop(
            columns=[
                c for c in ("rainfall", "temperature", "et0", "vpd", "enso_oni") if c in panel
            ],
            errors="ignore",
        ),
        "no_water": panel.drop(
            columns=[
                c
                for c in ("soil_moisture", "climatic_water_balance", "river_discharge")
                if c in panel
            ],
            errors="ignore",
        ),
        "no_market": panel.drop(
            columns=[
                c
                for c in panel.columns
                if "price" in c or (c.endswith("_index") and "food" in c) or c == "food_price_index"
            ],
            errors="ignore",
        ),
        "stats_only_climate_water": panel[
            [
                c
                for c in (
                    "rainfall",
                    "temperature",
                    "et0",
                    "soil_moisture",
                    "climatic_water_balance",
                    "river_discharge",
                )
                if c in panel.columns
            ]
        ],
    }
    out = {}
    for name, p in variants.items():
        if p.empty or p.shape[1] == 0:
            out[name] = {"alert": False, "reason": "empty"}
            continue
        d = detect(p, cutoff)
        g = build_graph(p, geo, cutoff)
        h = instantiate_hypotheses(geo, cutoff, d, g, [])
        out[name] = {
            "multi_signal_alert": d["multi_signal_alert"],
            "n_abnormal": d["n_abnormal"],
            "leading": h[0].template_id if h else None,
            "leading_posterior": h[0].score.posterior if h else None,
        }
    return out


def run_benchmark() -> dict:
    bench = load_benchmark()
    observations = _obs()
    results = []
    for event in bench["events"]:
        ev = evaluate_event(event, observations)
        ev["ablations"] = ablations(event, observations)
        results.append(ev)
    summary = {
        "n_events": len(results),
        "detected": sum((1 for r in results if r["multi_signal_alert_at_cutoff"])),
        "hypothesis_match": sum((1 for r in results if r["hypothesis_matches_documented"])),
        "mean_false_alarms": float(
            pd.Series([r["false_alarms_in_negative_windows"] for r in results]).mean()
        ),
        "notes": "False-alarm counts are months with multi-signal alerts inside documented negative windows. They are not a precision estimate over a global unlabeled stream. Lead time is first multi-signal month versus the conventional_visible_date in the event file.",
    }
    payload = {"summary": summary, "events": results, "benchmark": bench["name"]}
    out = EXPERIMENTS / "results" / "benchmark.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str))
    flat = pd.json_normalize(results)
    flat.to_csv(EXPERIMENTS / "results" / "benchmark.csv", index=False)
    return payload
