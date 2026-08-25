from __future__ import annotations

from datetime import date
import pandas as pd
from jaadu.core.config import all_regions
from jaadu.core.registry import unavailable, write_parquet
from jaadu.core.schemas import Availability, DatasetRecord, NodeType
from jaadu.core.time import apply_availability_lag, to_month
from jaadu.google.clients import earth_engine_ready, init_earth_engine

# MODIS 16-day vegetation composites are not same-day desk products.
NDVI_LAG_MONTHS = 1
LST_LAG_MONTHS = 1
START_DEFAULT = "2008-01-01"
END_DEFAULT = "2018-12-31"


def ndvi_available_at(valid_time: pd.Timestamp, lag_months: int = NDVI_LAG_MONTHS) -> pd.Timestamp:
    return apply_availability_lag(to_month(valid_time), lag_months)


def _unavailable_ee(reason: str) -> DatasetRecord:
    return unavailable(
        "modis_ndvi",
        "MODIS/VIIRS NDVI (Earth Engine)",
        "NASA MODIS via Google Earth Engine",
        "https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1",
        "multi",
        ["ndvi", "land_surface_temperature"],
        "Satellite vegetation activity independent of rainfall reanalysis.",
        reason,
    )


def _bbox_rect(region: dict) -> list[float]:
    box = region["bbox"]
    return [box["west"], box["south"], box["east"], box["north"]]


def _monthly_modis(region: dict, start: str, end: str) -> pd.DataFrame:
    import ee

    geom = ee.Geometry.Rectangle(_bbox_rect(region))
    start_d = ee.Date(start)
    end_d = ee.Date(end)
    n_months = end_d.difference(start_d, "month").toInt()
    ndvi_col = (
        ee.ImageCollection("MODIS/061/MOD13Q1").select("NDVI").filterBounds(geom).filterDate(start_d, end_d)
    )
    lst_col = (
        ee.ImageCollection("MODIS/061/MOD11A2")
        .select("LST_Day_1km")
        .filterBounds(geom)
        .filterDate(start_d, end_d)
    )

    def per_month(index):
        index = ee.Number(index)
        t0 = start_d.advance(index, "month")
        t1 = t0.advance(1, "month")
        ndvi = ndvi_col.filterDate(t0, t1).mean().multiply(0.0001)
        lst = lst_col.filterDate(t0, t1).mean().multiply(0.02).subtract(273.15)
        ndvi_mean = ndvi.reduceRegion(ee.Reducer.mean(), geom, 1000).get("NDVI")
        lst_mean = lst.reduceRegion(ee.Reducer.mean(), geom, 1000).get("LST_Day_1km")
        return ee.Feature(
            None,
            {
                "month": t0.format("YYYY-MM-dd"),
                "ndvi": ndvi_mean,
                "land_surface_temperature": lst_mean,
            },
        )

    fc = ee.FeatureCollection(ee.List.sequence(0, n_months.subtract(1)).map(per_month))
    info = fc.getInfo()
    rows = []
    for feat in info.get("features") or []:
        props = feat.get("properties") or {}
        month = props.get("month")
        if not month:
            continue
        ts = to_month(month)
        geo = region["id"]
        centroid = region.get("centroid") or {}
        for var, unit, node, lag, notes in (
            (
                "ndvi",
                "index",
                NodeType.AGRICULTURE,
                NDVI_LAG_MONTHS,
                "MOD13Q1 NDVI mean over region bbox; scaled. Not a yield observation.",
            ),
            (
                "land_surface_temperature",
                "C",
                NodeType.CLIMATE,
                LST_LAG_MONTHS,
                "MOD11A2 LST day mean over bbox, Kelvin scaled to C. Not air temperature.",
            ),
        ):
            value = props.get(var)
            if value is None:
                continue
            available = apply_availability_lag(ts, lag)
            rows.append(
                {
                    "observation_id": f"{geo}:{var}:{ts.date()}",
                    "variable": var,
                    "node_type": node.value,
                    "timestamp": ts.isoformat(),
                    "available_at": available.isoformat(),
                    "geo_id": geo,
                    "geo_resolution": "region_bbox",
                    "raw_value": float(value),
                    "value": float(value),
                    "unit": unit,
                    "source": "Google Earth Engine MODIS",
                    "source_url": "https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1",
                    "license": "NASA MODIS / GEE terms",
                    "transformation": "monthly_bbox_mean_lagged",
                    "quality_score": 0.78,
                    "source_reliability": 0.8,
                    "missingness": 0.0,
                    "availability": Availability.AVAILABLE.value,
                    "notes": notes,
                    "lat": centroid.get("lat"),
                    "lon": centroid.get("lon"),
                }
            )
    return pd.DataFrame(rows)


def ingest_earth_engine(
    start: str = START_DEFAULT, end: str | None = END_DEFAULT
) -> tuple[pd.DataFrame, list[DatasetRecord]]:
    end = end or END_DEFAULT
    if date.fromisoformat(end[:10]) < date.fromisoformat(start[:10]):
        raise ValueError("earth engine end before start")
    if not earth_engine_ready():
        rec = _unavailable_ee(
            "No authenticated Earth Engine session. Set GOOGLE_CLOUD_PROJECT and "
            "GOOGLE_APPLICATION_CREDENTIALS (or EARTHENGINE_SERVICE_ACCOUNT). "
            "NDVI is not imputed from rainfall."
        )
        return (pd.DataFrame(), [rec])
    try:
        init_earth_engine()
        frames = [_monthly_modis(region, start, end) for region in all_regions()]
        out = pd.concat([f for f in frames if f is not None and not f.empty], ignore_index=True)
        if out.empty:
            rec = _unavailable_ee("Earth Engine returned no monthly MODIS means for configured bboxes.")
            return (pd.DataFrame(), [rec])
        write_parquet(out, "observations_ee.parquet")
        record = DatasetRecord(
            dataset_id="modis_ndvi",
            name="MODIS NDVI and LST via Earth Engine",
            source="NASA MODIS / Google Earth Engine",
            url="https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1",
            country="multi",
            geographic_resolution="region_bbox",
            temporal_resolution="monthly_from_16day",
            start_date=start,
            end_date=end,
            units="NDVI index; LST C",
            license="NASA MODIS; Earth Engine ToS",
            update_frequency="16-day source, monthly mean here",
            known_limitations=(
                f"available_at is valid time plus {NDVI_LAG_MONTHS} month(s). "
                "This is not an operational nowcast. ERA5 rainfall remains a different product."
            ),
            missingness="bbox mean may be null under cloud/fill",
            quality_score=0.78,
            transformation="monthly_bbox_mean_lagged",
            variables=["ndvi", "land_surface_temperature"],
            why_it_matters="Independent vegetation evidence for agricultural-stress hypotheses.",
            status=Availability.AVAILABLE,
            citation="Didan, K. MOD13Q1 MODIS/Terra Vegetation Indices. NASA LP DAAC. GEE catalog.",
        )
        return (out, [record])
    except Exception as exc:
        rec = _unavailable_ee(f"Earth Engine export failed: {exc}. NDVI not imputed.")
        return (pd.DataFrame(), [rec])
