from __future__ import annotations

import time
from datetime import date
import httpx
import pandas as pd
from jaadu.core.config import DATA, all_regions
from jaadu.core.registry import unavailable, write_parquet
from jaadu.core.schemas import Availability, DatasetRecord, NodeType
from jaadu.core.time import apply_availability_lag, to_month

RAW = DATA / "raw"
RAW.mkdir(parents=True, exist_ok=True)
OPEN_METEO = "https://archive-api.open-meteo.com/v1/archive"
FLOOD_API = "https://flood-api.open-meteo.com/v1/flood"
WB_API = "https://api.worldbank.org/v2"
FAO_FPI = "https://www.fao.org/media/docs/worldfoodsituationlibraries/default-document-library/food_price_indices_data.csv?sfvrsn=523ebd2a_78&download=true"
ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv"
CLIMATE_DAILY = [
    "precipitation_sum",
    "temperature_2m_mean",
    "temperature_2m_max",
    "et0_fao_evapotranspiration",
    "soil_moisture_0_to_7cm",
    "vapour_pressure_deficit",
]
WB_INDICATORS = {
    "AG.YLD.CREL.KG": ("cereal_yield", "kg/ha", NodeType.AGRICULTURE),
    "AG.PRD.CROP.XD": ("crop_production_index", "index_2014_2016_100", NodeType.AGRICULTURE),
    "AG.PRD.FOOD.XD": ("food_production_index", "index_2014_2016_100", NodeType.AGRICULTURE),
    "EG.ELC.PROD.KH": ("electricity_generation", "kWh", NodeType.ENERGY),
}
FRED_SERIES = {
    "PWHEAMTUSDM": ("wheat_price", "usd/mt", NodeType.MARKET),
    "PRICENPQUSDM": ("rice_price", "usd/mt", NodeType.MARKET),
    "PMAIZMTUSDM": ("maize_price", "usd/mt", NodeType.MARKET),
    "PCOTTINDUSDM": ("cotton_price", "usd/kg", NodeType.MARKET),
    "PUGFERTUSDM": ("fertilizer_price", "index", NodeType.MARKET),
}


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=60.0, follow_redirects=True, headers={"User-Agent": "jaadu.exe/0.1 research"}
    )


def _retry_get(
    client: httpx.Client, url: str, params: dict | None = None, retries: int = 4
) -> httpx.Response:
    last = None
    for i in range(retries):
        try:
            r = client.get(url, params=params)
            r.raise_for_status()
            return r
        except Exception as exc:
            last = exc
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET failed {url}: {last}")


def fetch_open_meteo_station(
    client: httpx.Client, lat: float, lon: float, start: str, end: str
) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": ",".join(CLIMATE_DAILY),
        "timezone": "UTC",
    }
    r = _retry_get(client, OPEN_METEO, params)
    daily = r.json().get("daily") or {}
    if not daily or "time" not in daily:
        return pd.DataFrame()
    frame = pd.DataFrame(daily)
    frame["timestamp"] = pd.to_datetime(frame["time"])
    return frame


def fetch_glofas(
    client: httpx.Client, lat: float, lon: float, start: str, end: str
) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "river_discharge",
        "start_date": start,
        "end_date": end,
    }
    r = _retry_get(client, FLOOD_API, params)
    daily = r.json().get("daily") or {}
    if not daily or "time" not in daily:
        return pd.DataFrame()
    frame = pd.DataFrame(daily)
    frame["timestamp"] = pd.to_datetime(frame["time"])
    return frame


def monthly_climate(
    daily: pd.DataFrame, geo_id: str, station: str, lat: float, lon: float
) -> pd.DataFrame:
    if daily.empty:
        return daily
    d = daily.copy()
    d["month"] = d["timestamp"].dt.to_period("M").dt.to_timestamp()
    agg = d.groupby("month").agg(
        rainfall=("precipitation_sum", "sum"),
        temperature=("temperature_2m_mean", "mean"),
        temperature_max=("temperature_2m_max", "mean"),
        et0=("et0_fao_evapotranspiration", "sum"),
        soil_moisture=("soil_moisture_0_to_7cm", "mean"),
        vpd=("vapour_pressure_deficit", "mean"),
        n_days=("timestamp", "count"),
    )
    agg["climatic_water_balance"] = agg["rainfall"] - agg["et0"]
    agg = agg.reset_index().rename(columns={"month": "timestamp"})
    agg["geo_id"] = geo_id
    agg["station"] = station
    agg["lat"] = lat
    agg["lon"] = lon
    agg["missingness"] = (1 - agg["n_days"] / agg["timestamp"].dt.days_in_month).clip(0, 1)
    return agg


def to_long_observations(
    monthly: pd.DataFrame,
    variable_meta: dict[str, tuple[str, NodeType, str, str, float]],
    source: str,
    source_url: str,
    lag_months: int = 0,
    quality: float = 0.82,
) -> pd.DataFrame:
    rows = []
    for _, rec in monthly.iterrows():
        ts = to_month(rec["timestamp"])
        available = apply_availability_lag(ts, lag_months)
        for var, (unit, node_type, transform, notes, qadj) in variable_meta.items():
            if var not in rec or pd.isna(rec[var]):
                continue
            rows.append(
                {
                    "observation_id": f"{rec['geo_id']}:{var}:{ts.date()}",
                    "variable": var,
                    "node_type": node_type.value,
                    "timestamp": ts.isoformat(),
                    "available_at": available.isoformat(),
                    "geo_id": rec["geo_id"],
                    "geo_resolution": "point_centroid",
                    "raw_value": float(rec[var]),
                    "value": float(rec[var]),
                    "unit": unit,
                    "source": source,
                    "source_url": source_url,
                    "license": "see dataset registry",
                    "transformation": transform,
                    "quality_score": min(
                        1.0, quality * qadj * (1 - float(rec.get("missingness", 0)))
                    ),
                    "source_reliability": quality,
                    "missingness": float(rec.get("missingness", 0)),
                    "availability": Availability.AVAILABLE.value,
                    "notes": notes,
                    "station": rec.get("station"),
                    "lat": rec.get("lat"),
                    "lon": rec.get("lon"),
                }
            )
    return pd.DataFrame(rows)


def ingest_climate(
    start: str = "2005-01-01", end: str | None = None
) -> tuple[pd.DataFrame, list[DatasetRecord]]:
    end = end or date.today().isoformat()
    records: list[DatasetRecord] = []
    frames = []
    with _client() as client:
        for region in all_regions():
            geo = region["id"]
            for st in region.get("stations", []):
                daily = fetch_open_meteo_station(client, st["lat"], st["lon"], start, end)
                daily.to_csv(RAW / f"openmeteo_{geo}_{st['id']}.csv", index=False)
                monthly = monthly_climate(daily, geo, st["id"], st["lat"], st["lon"])
                meta = {
                    "rainfall": (
                        "mm",
                        NodeType.CLIMATE,
                        "monthly_sum_era5",
                        "ERA5 reanalysis via Open-Meteo, not rain-gauge",
                        0.95,
                    ),
                    "temperature": (
                        "C",
                        NodeType.CLIMATE,
                        "monthly_mean_era5",
                        "ERA5 2m temperature",
                        0.95,
                    ),
                    "et0": (
                        "mm",
                        NodeType.CLIMATE,
                        "monthly_sum_fao56",
                        "FAO-56 reference ET from Open-Meteo",
                        0.85,
                    ),
                    "soil_moisture": (
                        "m3/m3",
                        NodeType.WATER,
                        "monthly_mean_era5land",
                        "Shallow soil moisture; not root-zone NDVI",
                        0.75,
                    ),
                    "climatic_water_balance": (
                        "mm",
                        NodeType.WATER,
                        "rainfall_minus_et0",
                        "Derived water-balance proxy, not reservoir storage",
                        0.7,
                    ),
                    "vpd": (
                        "kPa",
                        NodeType.CLIMATE,
                        "monthly_mean",
                        "Vapour pressure deficit",
                        0.8,
                    ),
                }
                frames.append(
                    to_long_observations(
                        monthly,
                        meta,
                        source="Open-Meteo ERA5 archive",
                        source_url="https://open-meteo.com/en/docs/historical-weather-api",
                    )
                )
                try:
                    glofas = fetch_glofas(client, st["lat"], st["lon"], start, end)
                    glofas.to_csv(RAW / f"glofas_{geo}_{st['id']}.csv", index=False)
                    if not glofas.empty:
                        glofas["month"] = glofas["timestamp"].dt.to_period("M").dt.to_timestamp()
                        gagg = (
                            glofas.groupby("month")["river_discharge"]
                            .mean()
                            .reset_index()
                            .rename(columns={"month": "timestamp"})
                        )
                        gagg["geo_id"] = geo
                        gagg["station"] = st["id"]
                        gagg["lat"] = st["lat"]
                        gagg["lon"] = st["lon"]
                        gagg["missingness"] = 0.0
                        frames.append(
                            to_long_observations(
                                gagg,
                                {
                                    "river_discharge": (
                                        "m3/s",
                                        NodeType.WATER,
                                        "monthly_mean_glofas",
                                        "GloFAS river discharge reanalysis; proxy for hydrological state, not reservoir %",
                                        0.7,
                                    )
                                },
                                source="Open-Meteo Flood API / GloFAS",
                                source_url="https://open-meteo.com/en/docs/flood-api",
                                quality=0.72,
                            )
                        )
                except Exception as exc:
                    records.append(
                        unavailable(
                            f"glofas_{geo}_{st['id']}",
                            "GloFAS river discharge",
                            "ECMWF GloFAS via Open-Meteo",
                            FLOOD_API,
                            region["country"],
                            ["river_discharge"],
                            "Hydrological proxy for water availability.",
                            f"Fetch failed: {exc}",
                        )
                    )
    climate = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not climate.empty:
        write_parquet(climate, "observations_climate.parquet")
        records.append(
            DatasetRecord(
                dataset_id="openmeteo_era5",
                name="ERA5 climate via Open-Meteo",
                source="Open-Meteo / ECMWF ERA5",
                url="https://open-meteo.com/en/docs/historical-weather-api",
                country="multi",
                geographic_resolution="point (0.1° reanalysis neighborhood)",
                temporal_resolution="daily aggregated to monthly",
                start_date=start,
                end_date=end,
                units="mixed",
                license="Open-Meteo attribution; ERA5 Copernicus licence",
                update_frequency="historical archive",
                known_limitations="Reanalysis, not station gauges. Shallow soil moisture is not NDVI.",
                missingness="see observation missingness column",
                quality_score=0.82,
                transformation="monthly aggregation; water-balance = rain - ET0",
                variables=[
                    "rainfall",
                    "temperature",
                    "et0",
                    "soil_moisture",
                    "climatic_water_balance",
                    "vpd",
                ],
                why_it_matters="Meteorological and water-balance states that can precede agricultural outcomes.",
                status=Availability.AVAILABLE,
                citation="Hersbach et al. ERA5; Zippenfenig, Open-Meteo.",
            )
        )
        records.append(
            DatasetRecord(
                dataset_id="glofas_discharge",
                name="GloFAS river discharge",
                source="ECMWF GloFAS via Open-Meteo Flood API",
                url="https://www.globalfloods.eu/",
                country="multi",
                geographic_resolution="modelled river pixel at station centroid",
                temporal_resolution="daily aggregated to monthly",
                start_date=start,
                end_date=end,
                units="m3/s",
                license="C3S/GloFAS terms",
                update_frequency="historical archive",
                known_limitations="Not reservoir storage. Local river pixel may not match basin management volume.",
                missingness="varies by pixel",
                quality_score=0.7,
                transformation="monthly mean",
                variables=["river_discharge"],
                why_it_matters="Hydrological response lagged after rainfall, useful for pathway ordering.",
                status=Availability.AVAILABLE
                if "river_discharge" in climate.variable.values
                else Availability.DEGRADED,
                citation="Alfieri et al. GloFAS; Harrigan et al. GloFAS v4.",
            )
        )
    return (climate, records)


def ingest_world_bank() -> tuple[pd.DataFrame, list[DatasetRecord]]:
    records: list[DatasetRecord] = []
    rows = []
    with _client() as client:
        for iso in ("IND", "BRA"):
            for code, (var, unit, node_type) in WB_INDICATORS.items():
                url = f"{WB_API}/country/{iso}/indicator/{code}"
                try:
                    r = _retry_get(
                        client, url, {"format": "json", "per_page": 20000, "date": "2000:2024"}
                    )
                    payload = r.json()
                    series = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
                    raw = pd.DataFrame(series)
                    raw.to_csv(RAW / f"wb_{iso}_{code.replace('.', '_')}.csv", index=False)
                    for rec in series:
                        if rec.get("value") is None:
                            continue
                        year = int(rec["date"])
                        ts = pd.Timestamp(year=year, month=12, day=1)
                        geo = "india_national" if iso == "IND" else "brazil_national"
                        rows.append(
                            {
                                "observation_id": f"{geo}:{var}:{year}",
                                "variable": var,
                                "node_type": node_type.value,
                                "timestamp": ts.isoformat(),
                                "available_at": apply_availability_lag(ts, 8).isoformat(),
                                "geo_id": geo,
                                "geo_resolution": "country",
                                "raw_value": float(rec["value"]),
                                "value": float(rec["value"]),
                                "unit": unit,
                                "source": "World Bank Open Data",
                                "source_url": f"https://data.worldbank.org/indicator/{code}",
                                "license": "CC-BY 4.0",
                                "transformation": "annual official statistic",
                                "quality_score": 0.9,
                                "source_reliability": 0.9,
                                "missingness": 0.0,
                                "availability": Availability.DELAYED.value,
                                "notes": "National annual series; lagged. Not a leading indicator.",
                            }
                        )
                except Exception as exc:
                    records.append(
                        unavailable(
                            f"wb_{iso}_{code}",
                            f"World Bank {code}",
                            "World Bank",
                            url,
                            iso,
                            [var],
                            "Official agricultural/energy statistics for outcome baselines.",
                            str(exc),
                        )
                    )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        write_parquet(frame, "observations_worldbank.parquet")
        records.append(
            DatasetRecord(
                dataset_id="world_bank_ag_energy",
                name="World Bank agricultural and electricity statistics",
                source="World Bank Open Data",
                url="https://data.worldbank.org/",
                country="IND,BRA",
                geographic_resolution="national",
                temporal_resolution="annual",
                start_date="2000-12-01",
                end_date="2024-12-01",
                units="mixed",
                license="CC-BY 4.0",
                update_frequency="annual",
                known_limitations="Coarse geography and long publication lag. Used as outcome/baseline, not early signal.",
                missingness="indicator-dependent",
                quality_score=0.9,
                transformation="year assigned to December; +8 month availability lag",
                variables=list({v[0] for v in WB_INDICATORS.values()}),
                why_it_matters="Headline production/yield outcomes against which early detection is scored.",
                status=Availability.AVAILABLE,
                citation="World Bank World Development Indicators.",
            )
        )
    return (frame, records)


def ingest_fao_fpi() -> tuple[pd.DataFrame, list[DatasetRecord]]:
    records: list[DatasetRecord] = []
    try:
        with _client() as client:
            r = _retry_get(client, FAO_FPI)
        RAW.joinpath("fao_fpi.csv").write_bytes(r.content)
        raw = pd.read_csv(FAO_FPI if False else RAW / "fao_fpi.csv", skiprows=2)
        if "Date" not in raw.columns:
            raw = pd.read_csv(RAW / "fao_fpi.csv")
            raw.columns = [str(c).strip() for c in raw.columns]
        date_col = "Date" if "Date" in raw.columns else raw.columns[0]
        fpi_col = "Food Price Index" if "Food Price Index" in raw.columns else raw.columns[1]
        cereals_col = "Cereals" if "Cereals" in raw.columns else None
        frame = raw[[date_col, fpi_col] + ([cereals_col] if cereals_col else [])].copy()
        frame = frame.dropna(subset=[date_col])
        frame["timestamp"] = pd.to_datetime(frame[date_col], errors="coerce")
        frame = frame.dropna(subset=["timestamp"])
        rows = []
        mapping = [(fpi_col, "food_price_index", "index_2014_2016_100")]
        if cereals_col:
            mapping.append((cereals_col, "cereal_price_index", "index_2014_2016_100"))
        for _, rec in frame.iterrows():
            ts = to_month(rec["timestamp"])
            for col, var, unit in mapping:
                if pd.isna(rec[col]):
                    continue
                rows.append(
                    {
                        "observation_id": f"global:{var}:{ts.date()}",
                        "variable": var,
                        "node_type": NodeType.MARKET.value,
                        "timestamp": ts.isoformat(),
                        "available_at": apply_availability_lag(ts, 1).isoformat(),
                        "geo_id": "global_market",
                        "geo_resolution": "global",
                        "raw_value": float(rec[col]),
                        "value": float(rec[col]),
                        "unit": unit,
                        "source": "FAO Food Price Index",
                        "source_url": "https://www.fao.org/worldfoodsituation/foodpricesindex/en/",
                        "license": "FAO statistical database terms",
                        "transformation": "published index",
                        "quality_score": 0.93,
                        "source_reliability": 0.93,
                        "missingness": 0.0,
                        "availability": Availability.AVAILABLE.value,
                        "notes": "International prices, not Indian or Brazilian retail prices.",
                    }
                )
        out = pd.DataFrame(rows)
        write_parquet(out, "observations_fao_fpi.parquet")
        records.append(
            DatasetRecord(
                dataset_id="fao_fpi",
                name="FAO Food Price Index",
                source="FAO",
                url="https://www.fao.org/worldfoodsituation/foodpricesindex/en/",
                country="global",
                geographic_resolution="global",
                temporal_resolution="monthly",
                units="index 2014-2016=100",
                license="FAO terms of use",
                update_frequency="monthly",
                known_limitations="Not domestic retail. Used as international market pressure, not local food access.",
                missingness="low",
                quality_score=0.93,
                transformation="none",
                variables=["food_price_index", "cereal_price_index"],
                why_it_matters="Headline market indicator that conventional monitors watch. jaadu.exe should not wait for this.",
                status=Availability.AVAILABLE,
                citation="FAO Food Price Index methodology notes.",
            )
        )
        return (out, records)
    except Exception as exc:
        records.append(
            unavailable(
                "fao_fpi",
                "FAO Food Price Index",
                "FAO",
                FAO_FPI,
                "global",
                ["food_price_index"],
                "International food market pressure.",
                str(exc),
            )
        )
        return (pd.DataFrame(), records)


def ingest_fred() -> tuple[pd.DataFrame, list[DatasetRecord]]:
    records: list[DatasetRecord] = []
    frames = []
    with _client() as client:
        for sid, (var, unit, node_type) in FRED_SERIES.items():
            try:
                r = _retry_get(client, FRED, {"id": sid})
                path = RAW / f"fred_{sid}.csv"
                path.write_bytes(r.content)
                raw = pd.read_csv(path)
                value_col = [c for c in raw.columns if c != "DATE"][0]
                raw["timestamp"] = pd.to_datetime(raw["DATE"])
                raw["value"] = pd.to_numeric(raw[value_col], errors="coerce")
                raw = raw.dropna(subset=["value"])
                rows = []
                for _, rec in raw.iterrows():
                    ts = to_month(rec["timestamp"])
                    rows.append(
                        {
                            "observation_id": f"global:{var}:{ts.date()}",
                            "variable": var,
                            "node_type": node_type.value,
                            "timestamp": ts.isoformat(),
                            "available_at": ts.isoformat(),
                            "geo_id": "global_market",
                            "geo_resolution": "global",
                            "raw_value": float(rec["value"]),
                            "value": float(rec["value"]),
                            "unit": unit,
                            "source": f"FRED/{sid}",
                            "source_url": f"https://fred.stlouisfed.org/series/{sid}",
                            "license": "FRED terms; underlying World Bank/IMF commodity data",
                            "transformation": "published monthly",
                            "quality_score": 0.9,
                            "source_reliability": 0.9,
                            "missingness": 0.0,
                            "availability": Availability.AVAILABLE.value,
                            "notes": "International commodity price, not local mandi/CEPEA price.",
                        }
                    )
                frames.append(pd.DataFrame(rows))
                records.append(
                    DatasetRecord(
                        dataset_id=f"fred_{sid}",
                        name=f"FRED {sid} ({var})",
                        source="FRED / World Bank Pink Sheet",
                        url=f"https://fred.stlouisfed.org/series/{sid}",
                        country="global",
                        geographic_resolution="global",
                        temporal_resolution="monthly",
                        units=unit,
                        license="FRED terms",
                        update_frequency="monthly",
                        known_limitations="International prices. Local retail unavailable in this build.",
                        missingness="low",
                        quality_score=0.9,
                        transformation="none",
                        variables=[var],
                        why_it_matters="Market layer for fertilizer and staple commodities.",
                        status=Availability.AVAILABLE,
                        citation="Federal Reserve Bank of St. Louis FRED; World Bank Pink Sheet.",
                    )
                )
            except Exception as exc:
                records.append(
                    unavailable(
                        f"fred_{sid}",
                        f"FRED {sid}",
                        "FRED",
                        f"{FRED}?id={sid}",
                        "global",
                        [var],
                        "International commodity market signal.",
                        str(exc),
                    )
                )
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not out.empty:
        write_parquet(out, "observations_fred.parquet")
    return (out, records)


def ingest_oni() -> tuple[pd.DataFrame, list[DatasetRecord]]:
    records: list[DatasetRecord] = []
    try:
        with _client() as client:
            r = _retry_get(client, ONI_URL)
        RAW.joinpath("oni.ascii.txt").write_bytes(r.content)
        rows = []
        month_map = {
            "DJF": 1,
            "JFM": 2,
            "FMA": 3,
            "MAM": 4,
            "AMJ": 5,
            "MJJ": 6,
            "JJA": 7,
            "JAS": 8,
            "ASO": 9,
            "SON": 10,
            "OND": 11,
            "NDJ": 12,
        }
        for line in r.text.splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            (season, year_s, val) = (parts[0], parts[1], parts[2])
            if season not in month_map:
                continue
            try:
                year = int(year_s)
                oni = float(val)
            except ValueError:
                continue
            ts = pd.Timestamp(year=year, month=month_map[season], day=1)
            rows.append(
                {
                    "observation_id": f"global:enso_oni:{ts.date()}",
                    "variable": "enso_oni",
                    "node_type": NodeType.CLIMATE.value,
                    "timestamp": ts.isoformat(),
                    "available_at": apply_availability_lag(ts, 1).isoformat(),
                    "geo_id": "global_climate",
                    "geo_resolution": "global",
                    "raw_value": oni,
                    "value": oni,
                    "unit": "degC",
                    "source": "NOAA CPC Oceanic Niño Index",
                    "source_url": ONI_URL,
                    "license": "US public domain",
                    "transformation": "3-month running SST anomaly",
                    "quality_score": 0.95,
                    "source_reliability": 0.95,
                    "missingness": 0.0,
                    "availability": Availability.AVAILABLE.value,
                    "notes": "Large-scale climate context, not a local drought measure.",
                }
            )
        out = pd.DataFrame(rows)
        write_parquet(out, "observations_oni.parquet")
        records.append(
            DatasetRecord(
                dataset_id="noaa_oni",
                name="NOAA Oceanic Niño Index",
                source="NOAA CPC",
                url=ONI_URL,
                country="global",
                geographic_resolution="global",
                temporal_resolution="monthly (3-month seasons)",
                units="degC",
                license="US public domain",
                update_frequency="monthly",
                known_limitations="ENSO is a large-scale driver, not local rainfall.",
                missingness="none in published series",
                quality_score=0.95,
                transformation="season assigned to central month",
                variables=["enso_oni"],
                why_it_matters="2015 India drought is associated with El Niño; tests whether jaadu.exe uses context without treating ONI as destiny.",
                status=Availability.AVAILABLE,
                citation="NOAA Climate Prediction Center Oceanic Niño Index.",
            )
        )
        return (out, records)
    except Exception as exc:
        records.append(
            unavailable(
                "noaa_oni",
                "NOAA ONI",
                "NOAA CPC",
                ONI_URL,
                "global",
                ["enso_oni"],
                "El Niño context for monsoon risk.",
                str(exc),
            )
        )
        return (pd.DataFrame(), records)


def static_unavailable_records() -> list[DatasetRecord]:
    specs = [
        (
            "india_cwc_reservoirs",
            "India CWC reservoir storage",
            "Central Water Commission",
            "https://cwc.gov.in/",
            "IND",
            ["reservoir_storage"],
            "Direct hydrological management state for Marathwada.",
            "No redistributable monthly district/division series in this repository. Not imputed.",
        ),
        (
            "brazil_cantareira_volume",
            "Cantareira reservoir % volume",
            "SABESP / ANA",
            "https://www.sabesp.com.br/",
            "BRA",
            ["reservoir_storage"],
            "Headline conventional indicator for the 2014–15 São Paulo water crisis.",
            "Official storage series not redistributed. System treats this as the missing high-value observation.",
        ),
        (
            "modis_ndvi",
            "MODIS/VIIRS NDVI",
            "NASA / Copernicus",
            "https://modis.gsfc.nasa.gov/",
            "multi",
            ["ndvi"],
            "Satellite vegetation activity independent of rainfall reanalysis.",
            "No authenticated Earth-engine export in this prototype. Climatic water balance is a substitute proxy, labeled as such.",
        ),
        (
            "india_agmarknet",
            "Agmarknet mandi prices",
            "Government of India",
            "https://agmarknet.gov.in/",
            "IND",
            ["local_food_price"],
            "Local staple prices, the true food-access headline.",
            "No clean open historical API used here. International prices used instead and labeled global.",
        ),
        (
            "transport_disruptions",
            "Road/port disruption indicators",
            "multiple",
            "https://www.gdacs.org/",
            "multi",
            ["transport_disruption"],
            "Would distinguish logistics hypotheses from production hypotheses.",
            "No consistent open monthly series for 2013–2016 in the ingested corpus.",
        ),
        (
            "nutrition_surveys",
            "Nutrition / food-insecurity surveys",
            "NFHS / IBGE / IPC",
            "https://www.ipcinfo.org/",
            "multi",
            ["food_insecurity_prevalence"],
            "Population outcome layer.",
            "Surveys are infrequent and post-event. Unsuitable as early-warning inputs; marked unavailable.",
        ),
    ]
    return [unavailable(*s) for s in specs]
