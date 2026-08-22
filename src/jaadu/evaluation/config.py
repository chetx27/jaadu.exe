from __future__ import annotations

from jaadu.core.config import load_yaml, CONFIG


def load_robustness_spec() -> dict:
    return load_yaml(CONFIG / "experiments" / "robustness.yaml")


def load_benchmark_spec() -> dict:
    return load_yaml(CONFIG / "experiments" / "benchmark.yaml")
