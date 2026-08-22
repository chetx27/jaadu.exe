from __future__ import annotations

import pandas as pd
from jaadu.graph.temporal import build_graph


def monthly_snapshots(
    panel: pd.DataFrame, geo_id: str, start: str, end: str, step_months: int = 3
) -> list[dict]:
    stamps = pd.date_range(start, end, freq=f"{step_months}MS")
    snaps = []
    prev_edges = set()
    for ts in stamps:
        as_of = ts.strftime("%Y-%m-%d")
        sl = panel.loc[panel.index <= ts]
        if sl.empty or sl.shape[1] < 3:
            continue
        g = build_graph(sl, geo_id, as_of)
        keys = {(e["source"], e["target"], e["lag_months"]) for e in g["edges"]}
        born = keys - prev_edges
        died = prev_edges - keys
        snaps.append(
            {
                "as_of": as_of,
                "n_nodes": len(g["nodes"]),
                "n_edges": len(g["edges"]),
                "edges_born": [f"{a}->{b}:{lag}" for (a, b, lag) in sorted(born)],
                "edges_died": [f"{a}->{b}:{lag}" for (a, b, lag) in sorted(died)],
                "edges": g["edges"],
            }
        )
        prev_edges = keys
    return snaps


def edge_stability_table(snapshots: list[dict]) -> pd.DataFrame:
    counts = {}
    n = len(snapshots) or 1
    for snap in snapshots:
        for e in snap.get("edges", []):
            k = (e["source"], e["target"], e.get("lag_months", 0))
            counts[k] = counts.get(k, 0) + 1
    rows = [
        {
            "source": a,
            "target": b,
            "lag_months": lag,
            "presence_fraction": c / n,
            "n_snapshots": c,
        }
        for (a, b, lag), c in sorted(counts.items(), key=lambda kv: -kv[1])
    ]
    return pd.DataFrame(rows)
