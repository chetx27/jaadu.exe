from __future__ import annotations

import httpx
import pandas as pd
from jaadu.core.registry import unavailable
from jaadu.core.schemas import DatasetRecord
from jaadu.google import settings

DATA_GOV = "https://api.data.gov.in"
WHO_GHO = "https://ghoapi.azureedge.net/api"
IMD = "https://mausam.imd.gov.in/"
BHUVAN = "https://bhuvan-app1.nrsc.gov.in/"
FAOSTAT = "https://www.fao.org/faostat/en/#data"


def _try_get(url: str, params: dict | None = None, timeout: float = 20.0) -> tuple[bool, str]:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.get(url, params=params)
            if r.status_code >= 400:
                return False, f"HTTP {r.status_code} for {url}"
            return True, f"HTTP {r.status_code}"
    except Exception as exc:
        return False, str(exc)


def ingest_india_open() -> tuple[pd.DataFrame, list[DatasetRecord]]:
    """Attempt Indian and multilateral open portals. Never fabricate a series.

    Historical 2013–2016 mandi, IMD gauge, and Bhuvan archives are usually not
    redistributable as a clean monthly panel. Connectivity is recorded; missing
    layers stay UNAVAILABLE so VoI can still rank them.
    """
    records: list[DatasetRecord] = []
    probe = bool(settings.env("JAADU_PROBE_OPEN_DATA"))

    key = settings.data_gov_in_key()
    if not key:
        records.append(
            unavailable(
                "india_agmarknet",
                "Agmarknet mandi prices (data.gov.in)",
                "data.gov.in / Ministry of Agriculture",
                "https://www.data.gov.in/",
                "IND",
                ["local_food_price"],
                "Local staple prices, the true food-access headline.",
                "DATA_GOV_IN_API_KEY not set. Even with a key, the public Agmarknet "
                "resource is typically current-year and is not a 2015 replay archive. "
                "Not imputed from FAO/FRED.",
            )
        )
    else:
        ok, detail = _try_get(
            f"{DATA_GOV}/catalog/resource",
            params={"api-key": key, "format": "json", "limit": 1},
        )
        reason = (
            f"data.gov.in reachable: {detail}. Current catalog rows are not a 2015 monthly "
            "mandi panel; historical replay remains UNAVAILABLE so the cutoff cannot leak later prices."
            if ok
            else f"data.gov.in probe failed: {detail}. Mandi prices not imputed."
        )
        records.append(
            unavailable(
                "india_agmarknet",
                "Agmarknet mandi prices (data.gov.in)",
                "data.gov.in / Ministry of Agriculture",
                "https://www.data.gov.in/",
                "IND",
                ["local_food_price"],
                "Local staple prices, the true food-access headline.",
                reason,
            )
        )

    imd_detail = "not probed (set JAADU_PROBE_OPEN_DATA=1)"
    imd_ok = False
    if probe:
        imd_ok, imd_detail = _try_get(IMD)
    records.append(
        unavailable(
            "india_imd_gauges",
            "IMD district rainfall",
            "India Meteorological Department",
            IMD,
            "IND",
            ["rainfall_gauge"],
            "Gauge rainfall for Marathwada, distinct from ERA5 reanalysis.",
            (
                f"IMD portal probe: {imd_detail}. "
                if imd_ok
                else f"IMD portal: {imd_detail}. "
            )
            + "No redistributable monthly district gauge archive is ingested. ERA5 remains labeled reanalysis.",
        )
    )

    bhuvan_detail = "not probed (set JAADU_PROBE_OPEN_DATA=1)"
    bhuvan_ok = False
    if probe:
        bhuvan_ok, bhuvan_detail = _try_get(BHUVAN)
    records.append(
        unavailable(
            "india_bhuvan",
            "ISRO Bhuvan satellite products",
            "NRSC / ISRO Bhuvan",
            BHUVAN,
            "IND",
            ["ndvi_bhuvan"],
            "Indian-agency vegetation and land-use context alongside MODIS/GEE.",
            (
                f"Bhuvan probe: {bhuvan_detail}. "
                if bhuvan_ok
                else f"Bhuvan: {bhuvan_detail}. "
            )
            + "No authenticated historical export API used. Prefer Earth Engine MODIS when configured.",
        )
    )

    who_detail = "not probed (set JAADU_PROBE_OPEN_DATA=1)"
    who_ok = False
    if probe:
        who_ok, who_detail = _try_get(f"{WHO_GHO}/WHOSIS_000001", params={"$top": "1"})
    records.append(
        unavailable(
            "who_health_gho",
            "WHO Global Health Observatory",
            "World Health Organization",
            "https://www.who.int/data/gho",
            "multi",
            ["health_outcome"],
            "Population health outcomes are lagged; useful as context, not early warning.",
            (
                f"GHO probe: {who_detail}. "
                if who_ok
                else f"GHO: {who_detail}. "
            )
            + "Survey/estimate series are too lagged for cutoff discovery and are not ingested as leading features.",
        )
    )

    records.append(
        unavailable(
            "fao_national_food_balance",
            "FAOSTAT food-balance / crop statistics",
            "FAO",
            FAOSTAT,
            "multi",
            ["cereal_yield"],
            "National agricultural statistics complementary to World Bank WDI.",
            "FAOSTAT bulk is annual and lagged. World Bank cereal yield is already ingested with an 8-month availability lag. Not duplicated.",
        )
    )
    return (pd.DataFrame(), records)
