### jaadu.exe

**An investigation engine for emerging multi-domain failure pathways.**

Conventional early-warning systems wait for a predefined indicator to cross a threshold. jaadu.exe searches for *unspecified combinations of weak signals* that begin to move together, builds a temporal dependency graph, generates competing explanations, challenges the leading explanation, and computes the **value of additional information** — the cheapest or fastest observation that most reduces decision uncertainty.

This is a research prototype. It is **not** an operational warning service, **not** a chatbot, **not** a CSV-uploader, and **not** a claim that AI can predict disasters.

## The research question

Can a multimodal, temporal, graph-based system discover previously unspecified cross-domain failure structures *before* conventional outcome indicators become abnormal, while stating the evidence required to validate or reject its own hypotheses?

The answer is not assumed. It is measured in `experiments/results/` after you run the benchmark.

## What this is not

Existing systems already do drought monitoring (SPI, ASIS), food-security outlooks (FEWS NET, GIEWS, HungerMap LIVE), and price forecasting (NourishNet and many others). jaadu.exe does not replace them. The documented gap — see [`docs/research_audit.md`](docs/research_audit.md) — is the **closed loop** of:

1. multi-signal structure discovery (not a single forecast)
2. dynamic lagged dependency graphs labeled by *causal status*
3. competing mechanistic hypotheses with posteriors
4. an adversarial self-challenge step
5. decision-theoretic value of information
6. pre-event historical replay with leakage controls and baselines

If a production FEWS NET desk already does (1–6) as a quantitative, reproducible open pipeline, this prototype is a small open implementation of that loop, not a claim of first invention of early warning.

## Flagship demonstration

Food-system shock detection is a **domain configuration**, not the product identity.

| Role | Choice | Why |
|---|---|---|
| Product | Global failure-discovery engine | Country files are config |
| First laboratory | BRICS public data | India + Brazil where series actually exist |
| Flagship events | Marathwada 2015 drought; SE Brazil 2013–14 rainy-season failure | Documented multi-domain pathways and public pre-event climate data |
| Headline we refuse to output | “Food prices will rise 80%” | The system outputs a pathway, competitors, unknowns, and a next observation |

**Temporal splits (no future leakage into the model):**

- India Marathwada: cutoff **2015-08-01**; conventional visibility **2015-11-01** (kharif production / drought-impact reporting).
- São Paulo / Cantareira: cutoff **2013-12-01**; conventional visibility **2014-04-01** (reservoir emergency becoming public).

ERA5 is a reanalysis: values at a valid time are used as if they were available then, with an explicit caveat in [`docs/leakage.md`](docs/leakage.md). Official reservoir series and local mandi prices are **UNAVAILABLE** and are not imputed.

## Quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m jaadu ingest      # downloads public data (needs network)
python -m jaadu evaluate    # historical replay + baselines + ablations
python -m jaadu serve       # investigation UI at http://127.0.0.1:8000
```

Investigate one cutoff:

```bash
python -m jaadu investigate --region marathwada --as-of 2015-08-01
```

Optional Gemini extraction of dated documents:

```bash
cp .env.example .env   # set GEMINI_API_KEY
python -m jaadu investigate --region marathwada --as-of 2015-08-01 --gemini
```

Without an API key, documents are parsed by a deterministic heuristic extractor and labeled `heuristic_extraction`. Gemini is **not** the intelligence of the system.

Optional Google Cloud stack (Earth Engine NDVI, Maps, Translate, Speech, Dialogflow, Vertex baseline, Cloud Run):

```bash
pip install -e ".[google]"
# fill GOOGLE_CLOUD_PROJECT and related keys in .env
python -m jaadu google-status
```

Local ingest / evaluate / investigate still run with every Google variable empty. Earth Engine NDVI is lagged (`available_at` is valid time plus one month) and is never imputed from rainfall. Vertex AutoML is skipped unless `JAADU_VERTEX_BASELINE=1` and an endpoint are set; it is an evaluation comparator only. Cloud Run is the bench (`deploy/`), not a live ingest pipeline.

## Investigator workflow

1. Select a region and an as-of date.
2. jaadu.exe establishes a month-of-year baseline from history available at that date.
3. It flags persistent multi-signal anomalies (a single spike is not an alert).
4. It estimates lagged associations (PCMCI-lite + Granger screen).
5. It instantiates competing hypotheses and an adversary.
6. It ranks next observations by expected information gain / cost×time.
7. Only then may you reveal the held-out historical outcome.

Demo 2: perturb a variable (`POST /api/perturb`) — the graph and posteriors recompute.  
Demo 3: drop a dataset (`POST /api/ablate`) — missingness is explicit; VoI updates.

## Repository map

```
config/           countries, domain schema, engine thresholds, benchmark events
src/jaadu/    ingestion, validation, features, anomaly, graph, hypotheses,
                  counterfactuals, voi, multimodal, evaluation, baselines, api
data/registry/    dataset registry (written by ingest)
data/processed/   observation store (parquet) and investigation JSON
experiments/      benchmark definition outputs
docs/             audit, methodology, leakage, limitations, technical report
frontend/         investigation bench (not a KPI dashboard)
```

## Scientific honesty rules

- No fabricated accuracies, partnerships, or “real-time” claims.
- Correlation ≠ association ≠ causal hypothesis ≠ confirmed cause.
- Counterfactuals are **scenario analyses** unless identification assumptions are stated and defended (they are not, here).
- If ingest fails for a source, the variable is marked UNAVAILABLE.
- Experiment failures are recorded in `experiments/results/`, not hidden.
