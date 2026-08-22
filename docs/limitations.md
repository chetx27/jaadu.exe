# Limitations and failure modes

This prototype will look weaker under expert questioning if these are hidden. They are not.

1. **Two events do not make a global system.** India + Brazil are a laboratory. Precision/recall over “all crises” is not estimated.
2. **ERA5 ≠ IMD/INMET gauges.** Marathwada 2015 is well documented in gauge literature; our engine sees reanalysis.
3. **No reservoirs, no NDVI, no local prices.** Several competing hypotheses cannot be resolved; VoI is supposed to say so.
4. **PCMCI-lite is not Tigramite PCMCI.** Partial correlation, small parent sets, no hidden-variable methods (LPCMCI).
5. **Softmax hypothesis posteriors are not calibrated probabilities.** Do not treat 0.41 as “41% chance of drought.”
6. **VoI likelihoods are expert-specified.** They can be wrong; they are not fitted to the demo events.
7. **Isolation Forest on z-filled zeros** can create artifacts if many series are missing.
8. **National electricity/yield** cannot locate Marathwada or Campinas.
9. **Gemini** may hallucinate structure if used; we require passages and label interpretation vs extract. Heuristic fallback is weak NLP.
10. **Negative-control false alarms** may be real unlisted drought months (e.g. 2012 Maharashtra). Windows are imperfect.
11. **Thresholds** in `engine.yaml` are expert-defined and may be accidentally favorable to the two demos.
12. **Not real-time.** Ingest is batch. Do not demo as a live satellite operations center.
13. **No health, transport, or conflict layers.** Pathways involving those domains cannot be discovered.
14. **UI perturbation** adds a synthetic Δz; it is a sensitivity demo, not a physical forecast.

If evaluate shows no multi-signal alert at cutoff, that is a **valid experimental result**. Report it. Do not swap in post-event data to “fix” the demo.
