from __future__ import annotations

from datetime import date
import pandas as pd


def to_month(ts: str | pd.Timestamp | date) -> pd.Timestamp:
    return pd.Timestamp(ts).to_period("M").to_timestamp()


def month_range(start: str, end: str) -> pd.DatetimeIndex:
    return pd.date_range(to_month(start), to_month(end), freq="MS")


def apply_availability_lag(timestamp: pd.Timestamp, lag_months: int) -> pd.Timestamp:
    return (timestamp.to_period("M") + lag_months).to_timestamp()


def filter_as_of(frame: pd.DataFrame, cutoff: str, time_col: str = "available_at") -> pd.DataFrame:
    cut = pd.Timestamp(cutoff)
    ts = pd.to_datetime(frame[time_col])
    return frame.loc[ts <= cut].copy()


def valid_time_as_of(frame: pd.DataFrame, cutoff: str, time_col: str = "timestamp") -> pd.DataFrame:
    cut = pd.Timestamp(cutoff)
    ts = pd.to_datetime(frame[time_col])
    return frame.loc[ts <= cut].copy()
