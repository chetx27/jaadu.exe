from __future__ import annotations

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "config"
DATA = ROOT / "data"
EXPERIMENTS = ROOT / "experiments"


def load_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def engine_config() -> dict:
    return load_yaml(CONFIG / "engine.yaml")


def load_countries() -> dict[str, dict]:
    out = {}
    for p in (CONFIG / "countries").glob("*.yaml"):
        rec = load_yaml(p)
        out[rec["id"]] = rec
    return out


def load_domain(domain_id: str = "food_system") -> dict:
    return load_yaml(CONFIG / "domains" / f"{domain_id}.yaml")


def load_benchmark() -> dict:
    return load_yaml(CONFIG / "experiments" / "benchmark.yaml")


def all_regions() -> list[dict]:
    regions = []
    for country in load_countries().values():
        for region in country.get("regions", []):
            regions.append(region)
    return regions


def region_by_id(region_id: str) -> dict:
    for r in all_regions():
        if r["id"] == region_id:
            return r
    raise KeyError(region_id)
