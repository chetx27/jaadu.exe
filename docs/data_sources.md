# Dataset notes and citations

The machine-readable registry is written at ingest time to `data/registry/datasets.yaml`. This file explains *why* sources were chosen and which requested layers are absent.

## Ingested (intended)

| Dataset | Role | Citation / access |
|---|---|---|
| ERA5 via Open-Meteo historical API | Rainfall, temperature, ET0, shallow soil moisture | Hersbach et al., ERA5; Open-Meteo documentation |
| GloFAS via Open-Meteo flood API | River discharge proxy | Alfieri / Harrigan GloFAS papers; CEMS |
| NOAA CPC ONI | ENSO context | NOAA CPC ONI |
| FAO Food Price Index | International market headline | FAO FFPI methodology |
| FRED / World Bank Pink Sheet | Wheat, rice, maize, cotton, fertilizer index | FRED series pages; World Bank Commodity Markets |
| World Bank WDI | National cereal yield, crop production, electricity | WDI CC-BY |

## Explicitly unavailable (not fabricated)

| Layer | Why it would help | Why it is absent |
|---|---|---|
| CWC reservoir storage (Maharashtra divisions) | Distinguishes hydrological crisis from meteorological drought | No redistributable monthly series in this repo |
| SABESP Cantareira % volume | The conventional headline for 2014–15 | Not redistributed; VoI target |
| MODIS/VIIRS NDVI and LST | Independent vegetation / land-surface evidence | Google Earth Engine when `GOOGLE_CLOUD_PROJECT` (or a service account) is set; otherwise UNAVAILABLE. `available_at` = valid month + 1. Not a nowcast. |
| Agmarknet / data.gov.in local prices | True food-access indicator | Catalog stub; current-year APIs are not a 2015 replay archive |
| ISRO Bhuvan | Indian satellite context | No authenticated historical export in this repo |
| IMD district gauges | Gauge rainfall vs ERA5 | Portal recorded; monthly redistributable archive not ingested |
| WHO GHO | Health outcome context | Too lagged for cutoff discovery; UNAVAILABLE as a leading feature |
| Transport disruptions | Logistics hypothesis test | No consistent 2013–16 monthly open series ingested |
| Nutrition / IPC | Outcome layer | Surveys too lagged for early warning |

## Why each ingested family matters

- **Climate** can move first in drought pathways.
- **Water-balance and discharge** test whether the land surface responded — the difference between a rainfall blip and a hydrological anomaly.
- **National yield** is a *slow outcome*, used in evaluation, not as a leading feature (8-month lag).
- **International prices** are a conventional headline jaadu.exe should not wait for, and a confounder for “market-only” hypotheses.
- **ONI** tests whether the engine uses ENSO as context without treating it as destiny.
- **Earth Engine NDVI/LST** (when configured) is independent vegetation evidence with an explicit availability lag.
- **Text** supplies claims with provenance; it does not create rainfall numbers.

## Licenses

Respect Copernicus ERA5, FAO, World Bank, NOAA, and FRED terms. The MIT license covers jaadu.exe code only.
