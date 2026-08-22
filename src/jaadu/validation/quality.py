from __future__ import annotations

import pandas as pd


def quality_report(observations: pd.DataFrame) -> dict:
    if observations.empty:
        return {"n": 0, "variables": [], "sources": [], "geo_ids": []}
    frame = observations.copy()
    frame["value"] = pd.to_numeric(frame.get("value"), errors="coerce")
    agg_map = {
        "n": ("value", "size"),
        "missing": ("value", lambda s: float(s.isna().mean())),
        "tmin": ("timestamp", "min"),
        "tmax": ("timestamp", "max"),
    }
    if "quality_score" in frame.columns:
        agg_map["quality"] = ("quality_score", "mean")
    by_var = frame.groupby("variable").agg(**agg_map).reset_index()
    sources = (
        frame.groupby("source").size().reset_index(name="n").to_dict(orient="records")
        if "source" in frame.columns
        else []
    )
    return {
        "n": int(len(frame)),
        "n_variables": int(frame["variable"].nunique()),
        "n_geo": int(frame["geo_id"].nunique()) if "geo_id" in frame.columns else 0,
        "variables": by_var.to_dict(orient="records"),
        "sources": sources,
        "geo_ids": sorted(frame["geo_id"].dropna().unique().tolist()) if "geo_id" in frame.columns else [],
        "availability": frame["availability"].value_counts().to_dict()
        if "availability" in frame.columns
        else {},
    }
