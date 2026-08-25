# Data leakage prevention

jaadu.exe’s scientific claim is about *pre-event* discovery. The following rules are mandatory.

1. **Availability timestamps.** Features used at cutoff \(T\) must have `available_at <= T`. Valid time is not sufficient for lagged official statistics.
2. **Documents.** `published_at <= T`. Gadgil 2016 and Marengo 2015 papers are post-event relative to the India / Brazil cutoffs and must not appear in those replays.
3. **No target construction from the future.** We do not train a classifier on “months before crises” using labels that require the crisis date.
4. **No revision leakage.** We ingest current public archives. ERA5 and GloFAS are **retrospective reanalyses**. Using ERA5 at valid time \(t\) as if a 2015 desk had ERA5-quality fields is a **known optimistic bias**. It is disclosed here; it is not “real-time.” A stricter experiment would use only products published operationally in 2015 (e.g. then-current IMD, CHIRPS preliminary). That dataset is not in v0.1.
5. **Station centroids.** Point ERA5 extracts are not district means. Spatial leakage across adjacent districts is possible; Vidarbha is a coherence check, not a control trial.
6. **International prices.** FAO FPI and FRED commodities are global. They must not be described as Marathwada mandi prices.
7. **Gemini.** If used, the model sees only documents already admitted by (2). Prompts instruct: do not invent numbers. Retrieved text cannot change system instructions (documents are untrusted content).
8. **Photographs.** `published_at <= cutoff`. Vision output is `interpretation` and cannot write parquet observations.
9. **Earth Engine.** MODIS monthly means use `available_at` = valid time + 1 month. Do not treat a 2015-08 composite as a 2015-08-01 desk product.
10. **Translation / speech.** Language services may rewrite text; they do not change `published_at` or numeric values.
11. **Vertex.** Optional `evaluate` comparator. Never used to label training months as “pre-crisis” with future knowledge.
12. **Evaluation scans.** Negative-control windows are specified before looking at jaadu.exe outputs. Do not tune `engine.yaml` on the two flagship events and then report those same events as confirmation without labeling it as in-sample threshold choice. v0.1 thresholds are expert-defined a priori; they may still be accidentally favorable. Treat results as a **pilot**, not a locked benchmark.

See `config/experiments/benchmark.yaml` `leakage_rules`.
