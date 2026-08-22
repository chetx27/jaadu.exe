# Methodology

## 1. Observation model

Every numeric row is an `Observation` with `timestamp` (valid time), `available_at` (when a researcher in that month could have used it), geography, raw and processed value, unit, source, transformation, quality, and missingness.

Annual World Bank series for year Y are assigned valid time December Y and `available_at` += 8 months (expert-defined publication lag). Monthly FAO/FRED series use +0 or +1 month.

## 2. Seasonal baseline

For series \(x_t\), month-of-year median \(m_{mo(t)}\) and MAD \(s_{mo(t)}\) yield

\[
z_t = 0.6745 \frac{x_t - m_{mo(t)}}{s_{mo(t)}+\varepsilon}.
\]

A July rainfall is compared with Julys, not with January. This is not SPI (which fits a gamma). SPI remains a valid conventional baseline; we use robust z so that the same operator applies to ET, discharge, and prices.

## 3. Anomaly discovery

- **Point / contextual:** \(|z|\ge 1.5\) (weak), \(|z|\ge 2.5\) (conventional-strong). Expert-defined.
- **Persistence:** last \(k=2\) months all weak-or-strong.
- **Joint:** Mahalanobis \(p\) on the seasonal-z vector; Isolation Forest anomaly score; **combination surprise** = rarity of the active set co-occurring versus an independence baseline.
- **Alert rule:** at least 3 abnormal variables **and** (surprise > 0.4 **or** Mahalanobis \(p < 0.05\)). A single SPI-like spike is recorded (`conventional_univariate_hit`) but is **not** a jaadu.exe multi-signal alert.

## 4. Temporal graph (PCMCI-lite)

Full PCMCI (Runge et al. 2019) is not vendored. We implement:

1. Lagged correlation parent screening (\(\tau \le 6\) months).
2. Partial correlation of \(X_{t-\tau}\) with \(Y_t\) given a small parent set (momentary conditional independence analogue).
3. Fisher-z p-values; Granger F-test as a confirmation bit; rolling-window sign stability.

**Causal status:** correlation or evidence-supported association. Never confirmed causal. No contemporaneous orientation. Hidden confounding is assumed possible (reanalysis errors, shared seasonality residuals).

## 5. Hypotheses

Mechanism *templates* (environmental production shock, hydrological constraint, logistics, market, energy, artifact, seasonal) are classes, not a hardcoded Marathwada chain. Each template is scored on support, contradiction, temporal order of currently hot node types, spatial label, mechanism prior, and historical co-occurrence. Energies are converted to a softmax posterior. An **adversary** flags indistinguishability (\(\Delta\) posterior \(< 0.12\)), missing variables, and failed temporal order.

## 6. Counterfactual / scenario analysis

For a hypothesized driver set, we compare current downstream \(|z|\) with the mean downstream \(|z|\) in historical months where drivers were near baseline (\(|z|<0.5\)). This is **matched-period scenario analysis**. It is not difference-in-differences, not synthetic control, and not an ATE.

## 7. Value of information

Let \(H\) be the discrete hypothesis set with posterior \(p(h)\). A candidate observation \(X\) has a 3-level outcome and expert likelihoods \(p(x\mid h)\) (informative vs not). Then

\[
\mathrm{EIG}(X)= I(H;X)= H(H)-\mathbb{E}_x[H(H\mid x)].
\]

Rank by \(\mathrm{EIG}/(\mathrm{cost}\cdot(1+\lambda\,\mathrm{days}))\) with \(\lambda=0.15\). Likelihoods are **not learned from the event under test** (would leak). They are documented expert parameters in `voi/rank.py`.

## 8. Evaluation protocol

For each benchmark event:

- Hide all observations with `available_at > cutoff`.
- Hide documents with `published_at > cutoff`.
- Record multi-signal alert, leader template vs documented template, first alert month in the event window, lead days versus `conventional_visible_date`, false-alarm months in negative-control windows, baseline decisions at cutoff, whether a cross-domain edge was discovered, and whether VoI top-3 includes reservoir or NDVI (known missing, mechanism-relevant).

Ablations: drop climate, water, or market blocks; stats-only climate+water.

**Metrics we do not invent:** if evaluate has not been run, there is no accuracy number.
