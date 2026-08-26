"""Vertex AI as an optional evaluation comparator.

Never imported by investigate(). Offline `evaluate` stays deterministic unless
JAADU_VERTEX_BASELINE is explicitly enabled *and* an endpoint is configured.
A numeric score is not mapped to a jaadu.exe alert.
"""

from __future__ import annotations

import math
import pandas as pd
from jaadu.google import settings

BASELINE_NAME = "vertex_automl"


def _skip(reason: str) -> dict:
    return {
        "name": BASELINE_NAME,
        "alert": False,
        "skipped": True,
        "used_as_jaadu_alert": False,
        "reason": reason,
    }


def slice_as_of(panel: pd.DataFrame, as_of: str) -> pd.DataFrame:
    """Keep rows whose index is on or before the cutoff. Valid time ≠ available_at."""
    if panel.empty:
        return panel
    cut = pd.Timestamp(as_of)
    idx = pd.to_datetime(panel.index)
    return panel.loc[idx <= cut]


def instance_from_row(row: pd.Series) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, raw in row.items():
        if pd.isna(raw):
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        out[str(key)] = value
    return out


def parse_vertex_prediction(first: object) -> dict:
    """Record the model output. Do not invent an alert from an unlabeled score."""
    score = None
    model_alert = None
    if isinstance(first, dict):
        raw_score = first.get("score", first.get("anomalyScore"))
        if raw_score is not None:
            try:
                score = float(raw_score)
                if not math.isfinite(score):
                    score = None
            except (TypeError, ValueError):
                score = None
        if "alert" in first:
            model_alert = bool(first["alert"])
    else:
        try:
            score = float(first)  # type: ignore[arg-type]
            if not math.isfinite(score):
                score = None
        except (TypeError, ValueError):
            score = None
    return {
        "name": BASELINE_NAME,
        "alert": bool(model_alert) if model_alert is not None else False,
        "vertex_model_alert": model_alert,
        "score": score,
        "skipped": False,
        "used_as_jaadu_alert": False,
        "method": (
            "Vertex endpoint predict on the last as-of row only. "
            "Unlabeled scores are stored, not thresholded into a jaadu alert."
        ),
    }


def baseline_vertex(panel: pd.DataFrame, as_of: str, geo_id: str) -> dict:
    if not settings.vertex_baseline_opt_in():
        return _skip(
            "JAADU_VERTEX_BASELINE is not enabled. Vertex is an optional "
            "evaluate comparator, not the discovery engine."
        )
    endpoint = settings.vertex_baseline_endpoint()
    if not settings.project_id() or not endpoint:
        return _skip(
            "GOOGLE_CLOUD_PROJECT or VERTEX_BASELINE_ENDPOINT not set. "
            "Vertex is an optional comparator, not the discovery engine."
        )
    hist = slice_as_of(panel, as_of).select_dtypes("number").dropna(how="all")
    if hist.empty:
        return _skip("empty as-of panel")
    instance = instance_from_row(hist.iloc[-1])
    if not instance:
        return _skip("no finite numeric features at cutoff")
    try:
        from google.cloud import aiplatform

        aiplatform.init(project=settings.project_id(), location=settings.location())
        ep = aiplatform.Endpoint(endpoint)
        prediction = ep.predict(instances=[instance])
        preds = prediction.predictions or []
        parsed = parse_vertex_prediction(preds[0] if preds else {})
        parsed.update(
            {
                "geo_id": geo_id,
                "as_of": as_of,
                "n_features": len(instance),
                "feature_names": sorted(instance),
            }
        )
        return parsed
    except Exception as exc:
        return _skip(str(exc))
