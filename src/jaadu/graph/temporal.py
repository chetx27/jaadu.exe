from __future__ import annotations

import itertools
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests
from jaadu.core.config import engine_config, load_domain
from jaadu.core.schemas import CausalStatus, GraphEdge, GraphNode, NodeType, RelationshipType
from jaadu.features.seasonal import seasonalize_panel

VARIABLE_NODE_TYPE = {
    "rainfall": NodeType.CLIMATE,
    "temperature": NodeType.CLIMATE,
    "et0": NodeType.CLIMATE,
    "vpd": NodeType.CLIMATE,
    "enso_oni": NodeType.CLIMATE,
    "soil_moisture": NodeType.WATER,
    "climatic_water_balance": NodeType.WATER,
    "river_discharge": NodeType.WATER,
    "cereal_yield": NodeType.AGRICULTURE,
    "crop_production_index": NodeType.AGRICULTURE,
    "food_production_index": NodeType.AGRICULTURE,
    "fertilizer_price": NodeType.MARKET,
    "food_price_index": NodeType.MARKET,
    "cereal_price_index": NodeType.MARKET,
    "wheat_price": NodeType.MARKET,
    "rice_price": NodeType.MARKET,
    "maize_price": NodeType.MARKET,
    "cotton_price": NodeType.MARKET,
    "electricity_generation": NodeType.ENERGY,
}


def node_type_for(variable: str) -> NodeType:
    return VARIABLE_NODE_TYPE.get(variable, NodeType.EVENT)


def lagged_crosscorr(a: pd.Series, b: pd.Series, max_lag: int) -> tuple[int, float]:
    (best_lag, best) = (0, 0.0)
    joint = pd.concat([a, b], axis=1).dropna()
    if len(joint) < 24:
        return (0, 0.0)
    (x, y) = (joint.iloc[:, 0], joint.iloc[:, 1])
    for lag in range(0, max_lag + 1):
        if lag == 0:
            c = x.corr(y)
        else:
            c = x.shift(lag).corr(y)
        if pd.notna(c) and abs(c) > abs(best):
            (best, best_lag) = (float(c), lag)
    return (best_lag, float(best) if pd.notna(best) else 0.0)


def granger_p(a: pd.Series, b: pd.Series, max_lag: int) -> tuple[int, float]:
    joint = pd.concat([b, a], axis=1).dropna()
    if len(joint) < max(36, 8 * max_lag):
        return (0, 1.0)
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = grangercausalitytests(joint.values, maxlag=max_lag)
        (best_lag, best_p) = (1, 1.0)
        for lag, out in res.items():
            p = out[0]["ssr_ftest"][1]
            if p < best_p:
                (best_p, best_lag) = (float(p), int(lag))
        return (best_lag, best_p)
    except Exception:
        return (0, 1.0)


def partial_corr_lag(data: pd.DataFrame, src: str, tgt: str, lag: int, cond: list[str]) -> float:
    cols = {src, tgt, *cond}
    if any((c not in data.columns for c in cols)):
        return 0.0
    frame = data.copy()
    frame[f"{src}_lag"] = frame[src].shift(lag)
    use = [f"{src}_lag", tgt, *[c for c in cond if c != src]]
    sub = frame[use].dropna()
    if len(sub) < 30:
        return 0.0
    from numpy.linalg import lstsq

    def resid(y, X):
        X = np.column_stack([np.ones(len(X)), X])
        (b, *_) = lstsq(X, y, rcond=None)
        return y - X @ b

    y = sub[tgt].values
    x = sub[f"{src}_lag"].values
    if len(use) == 2:
        return float(np.corrcoef(x, y)[0, 1])
    Z = sub[use[2:]].values
    rx = resid(x, Z)
    ry = resid(y, Z)
    if rx.std() < 1e-09 or ry.std() < 1e-09:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


def pcmci_lite(z: pd.DataFrame, max_lag: int, alpha: float) -> list[GraphEdge]:
    cols = [c for c in z.columns if z[c].notna().sum() > 36]
    edges = []
    for tgt in cols:
        parents = []
        for src in cols:
            if src == tgt:
                continue
            (lag, c) = lagged_crosscorr(z[src], z[tgt], max_lag)
            if abs(c) >= 0.2:
                parents.append((src, lag, c))
        parents = sorted(parents, key=lambda t: -abs(t[2]))[:6]
        for src, lag, c0 in parents:
            cond = [p[0] for p in parents if p[0] != src][:3]
            pc = partial_corr_lag(z, src, tgt, max(lag, 1) if src != tgt else lag, cond)
            n = z[[src, tgt]].dropna().shape[0]
            if n < 20:
                continue
            fisher = np.arctanh(np.clip(pc, -0.999, 0.999))
            se = 1 / np.sqrt(max(n - len(cond) - 3, 3))
            from scipy.stats import norm

            p = float(2 * norm.sf(abs(fisher / se)))
            if p <= alpha and abs(pc) >= 0.12:
                edges.append(
                    GraphEdge(
                        edge_id=f"{src}->{tgt}:lag{lag}",
                        source=src,
                        target=tgt,
                        direction="forward",
                        lag_months=int(lag),
                        strength=float(pc),
                        uncertainty=float(min(1.0, p)),
                        p_value=p,
                        geographic_scope="panel",
                        relationship_type=RelationshipType.TEMPORAL_ASSOCIATION,
                        causal_status=CausalStatus.EVIDENCE_SUPPORTED_ASSOCIATION
                        if p < 0.01
                        else CausalStatus.CORRELATION,
                        method="pcmci_lite_partial_corr",
                    )
                )
    return edges


def rolling_stability(z: pd.DataFrame, src: str, tgt: str, lag: int, window: int) -> float:
    if src not in z or tgt not in z:
        return 0.0
    corrs = []
    idx = z.index
    if len(idx) < window + lag + 6:
        return 0.0
    for i in range(window, len(idx)):
        sl = z.iloc[i - window : i]
        (lag_c, c) = lagged_crosscorr(sl[src], sl[tgt], lag)
        if pd.notna(c):
            corrs.append(c)
    if not corrs:
        return 0.0
    sign_stable = np.mean(np.sign(corrs) == np.sign(np.median(corrs)))
    return float(sign_stable)


def build_graph(panel: pd.DataFrame, geo_id: str, as_of: str) -> dict:
    cfg = engine_config()
    cut = pd.Timestamp(as_of)
    hist = panel.loc[panel.index <= cut]
    z = seasonalize_panel(hist)
    nodes = []
    latest = z.iloc[-1] if not z.empty else pd.Series(dtype=float)
    for col in hist.columns:
        s = hist[col].dropna()
        nodes.append(
            GraphNode(
                node_id=col,
                variable=col,
                node_type=node_type_for(col),
                geo_id=geo_id,
                current_value=float(s.iloc[-1]) if not s.empty else None,
                seasonal_z=float(latest[col]) if col in latest and pd.notna(latest[col]) else None,
                trend=float(s.diff().tail(6).mean()) if len(s) > 6 else None,
                variance=float(s.tail(24).std()) if len(s) > 6 else None,
                data_quality=float(s.notna().mean()) if len(hist) else 0.0,
                confidence=0.5,
                n_obs=int(len(s)),
            )
        )
    edges = pcmci_lite(z, cfg["temporal"]["max_lag_months"], cfg["graph"]["pcmci_alpha"])
    for e in edges:
        (lag, p) = granger_p(z[e.source], z[e.target], max(e.lag_months, 1))
        e.evidence_count += 1 if p < cfg["graph"]["granger_alpha"] else 0
        e.historical_stability = rolling_stability(
            z, e.source, e.target, e.lag_months, cfg["graph"]["rolling_window_months"]
        )
        if (
            p < cfg["graph"]["granger_alpha"]
            and e.historical_stability >= cfg["graph"]["edge_stability_min"]
        ):
            e.causal_status = CausalStatus.EVIDENCE_SUPPORTED_ASSOCIATION
        else:
            e.causal_status = CausalStatus.CORRELATION
        e.geographic_scope = geo_id
        e.window_end = as_of
    return {
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in edges],
        "as_of": as_of,
        "geo_id": geo_id,
        "method_notes": "Edges are lagged associations after a PCMCI-lite partial-correlation screen and a Granger confirmation pass. They are not confirmed causal effects.",
    }


def anomalous_subgraph(graph: dict, detection: dict, z_threshold: float = 1.5) -> list[str]:
    hot = {
        s["variable"]
        for s in detection.get("current_signals", [])
        if abs(s["seasonal_z"]) >= z_threshold
    }
    path = []
    domain = load_domain()
    order = {t: i for (i, t) in enumerate(domain["node_types"])}
    nodes = {n["node_id"]: n for n in graph["nodes"]}
    ranked = sorted(hot, key=lambda v: (order.get(nodes.get(v, {}).get("node_type"), 99), v))
    used = set()
    for src, tgt in itertools.permutations(ranked, 2):
        for e in graph["edges"]:
            if e["source"] == src and e["target"] == tgt and ((src, tgt) not in used):
                path.append(f"{src} -[{e['lag_months']}m, {e['causal_status']}]-> {tgt}")
                used.add((src, tgt))
    if not path:
        path = ranked
    return path
