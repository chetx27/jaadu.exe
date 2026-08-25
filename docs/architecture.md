# Architecture

jaadu.exe is a **batch investigation engine** with an HTTP façade. It is not a streaming “real-time” platform. Updates occur when ingest is rerun.

```
                    ┌─────────────────────────────────────────┐
  Public APIs  ──►  │ ingestion   validation   observation     │
  Dated docs   ──►  │ store (parquet) + dataset registry        │
                    └───────────────┬─────────────────────────┘
                                    │ as-of filter
                    ┌───────────────▼─────────────────────────┐
                    │ seasonal features · anomaly discovery     │
                    │ PCMCI-lite graph · hypothesis simplex     │
                    │ adversary · scenario analysis · VoI       │
                    └───────────────┬─────────────────────────┘
                                    │
                    ┌───────────────▼─────────────────────────┐
                    │ investigation JSON · FastAPI · UI bench  │
                    │ evaluation / baselines / ablations       │
                    └─────────────────────────────────────────┘
```

## Module contracts

| Module | Deterministic? | May call an LLM? |
|---|---|---|
| ingestion, validation, time filters | yes | no |
| seasonal z, CUSUM, Mahalanobis, IsolationForest | yes (seeded) | no |
| PCMCI-lite, Granger | yes | no |
| hypothesis scoring, VoI EIG | yes | no |
| document → EvidenceObject | heuristic default | Gemini optional; Translation API first if language ≠ working language |
| citizen photograph | caption-only default | Gemini multimodal optional; always `interpretation` |
| UI map | Leaflet | Google Maps JS if `MAPS_BROWSER_KEY` |
| voice brief / Dialogflow | off | Cloud TTS / Dialogflow webhook calling existing APIs |
| evaluation baseline | seasonal z, IF, rules, retrieval | Vertex endpoint optional and skipped without credentials |
| UI copy | static | no |

Gemini, when configured, **only** structures dated documents into `EvidenceObject`s. It cannot write numeric observations and cannot bypass `available_at <= cutoff`. Earth Engine writes lagged NDVI/LST observations with explicit `available_at`. Dialogflow and Cloud TTS are investigator I/O. Vertex is not called from `investigate()`.

## World state

A region-month panel is the working representation. Nodes are variables (climate, water, agriculture, market, energy, …). Missing domain layers remain in the registry as `UNAVAILABLE`.

Edges carry: lag, strength, p-value, stability, `relationship_type`, and `causal_status` ∈ {correlation, evidence_supported_association, causal_hypothesis, confirmed_causal}. **Nothing in this prototype is `confirmed_causal`.**

## Adding a country

1. Create `config/countries/<name>.yaml` with regions and station centroids.
2. Rerun ingest (Open-Meteo uses those coordinates).
3. Add an event to `config/experiments/benchmark.yaml` only if a documented outcome and cutoff exist.
4. Do not change `src/jaadu/anomaly`, `graph`, `hypotheses`, or `voi`.

Food security is `config/domains/food_system.yaml`. A water-stress or energy configuration would swap watched variables and mechanism templates, not the engine.

## Thresholds

`config/engine.yaml` labels expert-defined constants. Isolation Forest contamination is also expert-defined (0.08), not cross-validated in v0.1. Learned objects, if any, must be written under `experiments/results/` with a seed (`42`).
