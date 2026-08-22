from __future__ import annotations

import numpy as np
import pandas as pd


def lead_days(detection_date: str | None, conventional_date: str) -> int | None:
    if detection_date is None:
        return None
    return int((pd.Timestamp(conventional_date) - pd.Timestamp(detection_date)).days)


def false_alarm_rate(n_false: int, n_negative_months: int) -> float:
    if n_negative_months <= 0:
        return float("nan")
    return n_false / n_negative_months


def binary_scores(detected: list[bool], labeled: list[bool]) -> dict:
    tp = sum(1 for d, y in zip(detected, labeled) if d and y)
    fp = sum(1 for d, y in zip(detected, labeled) if d and not y)
    fn = sum(1 for d, y in zip(detected, labeled) if not d and y)
    tn = sum(1 for d, y in zip(detected, labeled) if not d and not y)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "false_alarm_rate": fp / (fp + tn) if fp + tn else 0.0,
    }


def brier_score(probs: list[float], labels: list[int]) -> float:
    if not probs:
        return float("nan")
    p = np.asarray(probs, dtype=float)
    y = np.asarray(labels, dtype=float)
    return float(np.mean((p - y) ** 2))


def hypothesis_rank_quality(leader: str | None, documented: str) -> dict:
    return {
        "documented": documented,
        "leader": leader,
        "match": leader == documented,
        "note": "Template match is not mechanistic proof. Documented labels are expert encodings of literature.",
    }


def summarize_event_row(row: dict) -> dict:
    return {
        "event_id": row.get("event_id"),
        "detected": row.get("multi_signal_alert_at_cutoff"),
        "lead_days": row.get("lead_days_vs_conventional"),
        "hypothesis_match": row.get("hypothesis_matches_documented"),
        "false_alarms": row.get("false_alarms_in_negative_windows"),
        "cross_domain_edge": row.get("discovered_cross_domain_edge"),
    }
