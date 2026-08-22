# Research audit: closest systems and the defensible gap

jaadu.exe was not designed until this audit existed. The goal is to avoid rediscovering FEWS NET and calling it novel.

## What already exists (selected)

### Operational food / drought early warning

| System | What it does | What it does not do (open, quantitative, closed loop) |
|---|---|---|
| **FEWS NET** (USAID + USGS + others) | Expert-driven food-security outlooks; drought early warning using SST, atmosphere, land surface; scenario analysis by regional analysts | Automated discovery of *unspecified* multi-domain pathways; competing-hypothesis posteriors; VoI ranking of next measurements; fully reproducible open pipeline a third party can rerun |
| **FAO GIEWS / FPMA** | Crop monitoring, price anomaly indicator (SDG 2.c.1), bulletins | Pathway discovery; the Indicator of Price Anomalies is a *predefined* headline |
| **FAO ASIS** | Vegetation-health agricultural stress index from satellites, ~dekadal | Single-family (vegetation) monitor, not cross-domain hypothesis competition |
| **WFP HungerMap LIVE** | Near-real-time hunger tracking, ML where surveys are missing | Outcome nowcasting/mapping, not pre-threshold pathway discovery with VoI |
| **National drought monitors** (IMD, INMET, USDM, etc.) | SPI/SPEI, drought declarations | Predefined meteorological/hydrological indices |

Citations: Funk et al. on FEWS NET DEWS (USGS/BAMS lineage); FAO GIEWS data-tools pages; Rojas, Rembold and ASIS technical notes; WFP HungerMap product notes.

### Academic and prototype systems

| Work | Overlap | Difference |
|---|---|---|
| NourishNet (arXiv:2407.00698) | Food-price warning labels from GIEWS | Forecasts a price state, not a multi-domain pathway |
| CIRAD/heterogeneous FS prediction | ML on mixed FS indicators | Supervised prediction of known FS scores |
| HazardGraph (open prototype) | Ensemble + VARLiNGAM + graphs for Horn of Africa food security | Crisis prediction / alert dispatch; not the competing-hypothesis + decision-theoretic VoI investigation loop on BRICS public series with pre-event replay |
| PCMCI / Tigramite (Runge et al., *Science Advances* 2019) | Lagged causal discovery for climate | A method we *use a lite form of*; not a civic investigation product |
| Temporal knowledge graphs for crises (Gastinger et al.) | Dynamic graphs of conflict/trade | Event forecasting on TKGs, not food-system weak-signal discovery |
| Graph anomaly + counterfactuals (various 2023–2025 GAD papers) | Counterfactual graphs for *model explanation* | Different object: explaining GNN detectors, not testing physical failure hypotheses |
| INCADET / MOCHA | Incremental causal graphs | Cyber-physical / clinical, not public food-system replay |

### Value of information / active sensing

Raiffa & Schlaifer decision theory; Lindley on expected information; climate observing-system simulation experiments (OSSEs); sensor-placement via mutual information. **EIG = I(H; X)** over a discrete hypothesis set is standard. Using it to rank *the next civic measurement* inside an early-warning investigation UI is uncommon in open food-security software.

## Novelty we will *not* claim

- Early warning systems are not new.
- Multimodal AI is not new.
- Causal discovery on climate series is not new.
- “AI for disasters” is not new.

## Smallest technically defensible gap

**Open, reproducible discovery of emerging *unspecified* cross-domain anomalous structures, with explicit causal-status labels, competing mechanistic hypotheses, adversarial challenge, and decision-theoretic value of information, evaluated by pre-event replay against conventional baselines — without leaking post-event documents or outcome statistics.**

That combination is the contribution. Individual modules are borrowed and cited.

If a reviewer points to a system that already implements this full loop on public data with a replay protocol, jaadu.exe should be reframed as a comparative reimplementation, not as a new scientific object. We did not find such an open stack in this audit, but absence of evidence is not evidence of absence.

## Design consequences of the audit

1. Do **not** build another SPI dashboard or price forecaster as the core.
2. Do **not** hard-code rainfall → prices.
3. Do **not** let Gemini produce the alert.
4. Do **not** treat PCMCI edges as causes.
5. Do **evaluate** lead time versus a conventional date, false-alarm months in negative windows, hypothesis match to a documented template, and whether VoI ranks actually-missing high-value variables (reservoir, NDVI).
