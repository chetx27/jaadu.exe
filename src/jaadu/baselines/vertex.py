"""Vertex AI as an optional evaluation comparator.

Not wired into investigate(). If GOOGLE_CLOUD_PROJECT or a dedicated endpoint
is missing, the baseline is skipped so `evaluate` stays deterministic offline.
"""

from __future__ import annotations

import pandas as pd
from jaadu.google import settings


def baseline_vertex(panel: pd.DataFrame, as_of: str, geo_id: str) -> dict:
    endpoint = settings.vertex_baseline_endpoint()
    if not settings.project_id() or not endpoint:
        return {
            "name": "vertex_automl",
            "alert": False,
            "skipped": True,
            "reason": "GOOGLE_CLOUD_PROJECT or VERTEX_BASELINE_ENDPOINT not set. Vertex is an optional comparator, not the discovery engine.",
        }
    hist = panel.loc[:as_of].select_dtypes("number").dropna()
    if hist.empty:
        return {"name": "vertex_automl", "alert": False, "skipped": True, "reason": "empty panel"}
    try:
        from google.cloud import aiplatform

        aiplatform.init(project=settings.project_id(), location=settings.location())
        ep = aiplatform.Endpoint(endpoint)
        instances = [hist.iloc[-1].to_dict()]
        prediction = ep.predict(instances=instances)
        preds = prediction.predictions or []
        score = None
        alert = False
        if preds:
            first = preds[0]
            if isinstance(first, dict):
                score = float(first.get("score") or first.get("anomalyScore") or 0)
                alert = bool(first.get("alert") or score > 0.5)
            else:
                score = float(first)
                alert = score > 0.5
        return {
            "name": "vertex_automl",
            "alert": bool(alert),
            "score": score,
            "skipped": False,
            "method": "vertex endpoint predict on last as-of row; not used for jaadu alerts",
            "geo_id": geo_id,
        }
    except Exception as exc:
        return {"name": "vertex_automl", "alert": False, "skipped": True, "reason": str(exc)}
