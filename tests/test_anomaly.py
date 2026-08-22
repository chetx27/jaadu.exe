from __future__ import annotations

import numpy as np
import pandas as pd
from jaadu.anomaly.detect import detect, joint_combination_surprise
from jaadu.features.seasonal import seasonalize_panel


def _panel(n=96, drought=True):
    idx = pd.date_range("2008-01-01", periods=n, freq="MS")
    month = idx.month
    rain = 80 + 40 * np.sin(2 * np.pi * (month - 7) / 12)
    et = 90 + 20 * np.sin(2 * np.pi * (month - 5) / 12)
    if drought:
        rain[-8:] = rain[-8:] * 0.35
        et[-8:] = et[-8:] * 1.15
    soil = 0.25 + 0.05 * np.sin(2 * np.pi * month / 12)
    if drought:
        soil[-6:] = soil[-6:] * 0.6
    return pd.DataFrame(
        {"rainfall": rain, "et0": et, "soil_moisture": soil, "climatic_water_balance": rain - et},
        index=idx,
    )


def test_joint_surprise_needs_multiple_variables():
    z = seasonalize_panel(_panel(drought=False))
    out = joint_combination_surprise(z, z.index[-1].strftime("%Y-%m-%d"), 10.0)
    assert out["surprise"] == 0.0


def test_detect_returns_required_keys():
    p = _panel()
    as_of = p.index[-1].strftime("%Y-%m-%d")
    d = detect(p, as_of, include_isolation=False)
    for k in ("multi_signal_alert", "n_abnormal", "current_signals", "combination"):
        assert k in d
