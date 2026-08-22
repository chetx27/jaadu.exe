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
| MODIS/VIIRS NDVI | Independent vegetation evidence | No Earth Engine export in v0.1 |
| Agmarknet / CEPEA local prices | True food-access indicator | No clean historical API used here |
| Transport disruptions | Logistics hypothesis test | No consistent 2013–16 monthly open series ingested |
| Nutrition / IPC | Outcome layer | Surveys too lagged for early warning |

## Why each ingested family matters

- **Climate** can move first in drought pathways.
- **Water-balance and discharge** test whether the land surface responded — the difference between a rainfall blip and a hydrological anomaly.
- **National yield** is a *slow outcome*, used in evaluation, not as a leading feature (8-month lag).
- **International prices** are a conventional headline jaadu.exe should not wait for, and a confounder for “market-only” hypotheses.
- **ONI** tests whether the engine uses ENSO as context without treating it as destiny.
- **Text** supplies claims with provenance; it does not create rainfall numbers.

## Licenses

Respect Copernicus ERA5, FAO, World Bank, NOAA, and FRED terms. The MIT license covers jaadu.exe code only.
