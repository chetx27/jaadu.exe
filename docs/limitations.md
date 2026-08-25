# Limitations and failure modes

This prototype will look weaker under expert questioning if these are hidden. They are not.

1. **Two events do not make a global system.** India + Brazil are a laboratory. Precision/recall over “all crises” is not estimated.
2. **ERA5 ≠ IMD/INMET gauges.** Marathwada 2015 is well documented in gauge literature; our engine sees reanalysis.
3. **No reservoirs, limited NDVI, no local prices.** CWC/SABESP storage and Agmarknet remain UNAVAILABLE unless you bring a redistributable archive. Earth Engine NDVI appears only with GCP credentials and is lagged by one month. VoI is supposed to rank the rest.
4. **PCMCI-lite is not Tigramite PCMCI.** Partial correlation, small parent sets, no hidden-variable methods (LPCMCI).
5. **Softmax hypothesis posteriors are not calibrated probabilities.** Do not treat 0.41 as “41% chance of drought.”
6. **VoI likelihoods are expert-specified.** They can be wrong; they are not fitted to the demo events.
7. **Isolation Forest on z-filled zeros** can create artifacts if many series are missing.
8. **National electricity/yield** cannot locate Marathwada or Campinas.
9. **Gemini / vision** may hallucinate structure if used; photographs are always `interpretation`. Heuristic fallback is weak NLP.
10. **Negative-control false alarms** may be real unlisted drought months (e.g. 2012 Maharashtra). Windows are imperfect.
11. **Thresholds** in `engine.yaml` are expert-defined and may be accidentally favorable to the two demos.
12. **Not real-time.** Ingest is batch, including Earth Engine composites. Cloud Run hosts the bench; it is not a live satellite operations center.
13. **No health, transport, or conflict layers as leading features.** WHO/GHO and transport remain UNAVAILABLE on purpose.
14. **UI perturbation** adds a synthetic Δz; it is a sensitivity demo, not a physical forecast.
15. **Dialogflow** cannot reveal held-out outcomes and does not generate hypotheses.

If evaluate shows no multi-signal alert at cutoff, that is a **valid experimental result**. Report it. Do not swap in post-event data to “fix” the demo.
