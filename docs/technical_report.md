# Technical report (pilot)

jaadu.exe is a research prototype for discovering emerging multi-domain failure structures from public time series and dated documents. It is not an operational early-warning service.

## Question

Can a system that (i) flags joint seasonal anomalies, (ii) estimates lagged associations, (iii) ranks competing mechanistic templates, and (iv) computes decision-theoretic value of information detect a documented food/water pathway *before* a conventional visibility date, without leaking post-cutoff evidence?

## Method (short)

- Observations carry `timestamp` and `available_at`. Features at cutoff T use `available_at <= T`.
- Seasonal robust z-scores (month-of-year median/MAD).
- Multi-signal alert: at least three abnormal variables and either combination surprise or Mahalanobis p < 0.05. A single conventional spike is recorded but is not the alert.
- PCMCI-lite partial correlation + Granger screen. Edges are observational, never `confirmed_causal`.
- Hypothesis templates are classes (environmental production shock, hydrological constraint, logistics, market, energy, artifact, seasonal). Softmax over heuristic energies is **not** a calibrated probability.
- VoI is expected information gain I(H; X) with expert likelihoods, ranked by EIG / (cost × time).
- Counterfactuals are matched-period scenarios, not ATEs.

## Data

India (Marathwada, Vidarbha) and Brazil (São Paulo / Cantareira) via ERA5/Open-Meteo, GloFAS discharge, NOAA ONI, FAO Food Price Index, FRED commodities, World Bank annual agriculture/energy. Reservoir storage, NDVI, local prices, transport, and nutrition surveys are **UNAVAILABLE** and not imputed.

## Evaluation protocol

See `config/experiments/benchmark.yaml`. Cutoffs:

- Marathwada 2015: 2015-08-01 vs conventional 2015-11-01
- SE Brazil 2014: 2013-12-01 vs conventional 2014-04-01

Baselines: seasonal univariate z, Isolation Forest, SPI-like rainfall rule, dated-document retrieval.

Run:

```
python -m jaadu ingest
python -m jaadu evaluate
```

Numbers live in `experiments/results/benchmark.json`. This report does not invent them. If that file is absent, no accuracy claim is made.

## Known biases

ERA5 is a reanalysis (see `docs/leakage.md`). Expert thresholds in `config/engine.yaml` were not locked on an independent event set. Two events are a pilot, not a global precision estimate.

## What would falsify the thesis

- Multi-signal alerts only when a single rainfall z already exceeds 2.5, with no extra pathway structure.
- Leading templates matching documented mechanisms at chance after multiple events.
- VoI ranking variables that are already in the panel or that cannot distinguish hypotheses.
- Leakage audit failures (`python -m jaadu leakage-audit`).
