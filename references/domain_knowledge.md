# Domain Knowledge Reference — Herbal Essential Oil Extraction

RAG/grounding reference used to keep agent outputs grounded. Tier labels
follow the evidence hierarchy in `SECOND-KNOWLEDGE-BRAIN.md` Section 1.2.

## Evidence hierarchy (this domain)
- **Tier 1** — Systematic review / meta-analysis / official standard (ISO,
  WHO, pharmacopoeia).
- **Tier 2** — Peer-reviewed academic paper / RCT / validated method.
- **Tier 3** — Industry report / professional-association guideline.
- **Tier 4** — News / blog / vendor material.

## Chemotype guidance (selected)
- **Lavender:** linalool + linalyl acetate dominant; SFE-CO2 preserves
  esters; steam acceptable but watch linalyl acetate hydrolysis.
- **Peppermint:** menthol-dominant; menthofuran is an oxidation marker —
  keep <1–5%; steam standard.
- **Clove:** eugenol 75–90%; high yield; steam robust.
- **Lemongrass:** citral (geranial + neral) dominant; aldehydes are
  thermolabile → SFE-CO2 preferred for aroma.
- **Rosemary:** 1,8-cineole or camphor chemotypes; method per target.

## Yield baselines (% w/w, dry basis, mature material)
See `tools/yield_estimator.py` `BASELINE_YIELDS` for the canonical numeric
ranges used by the runtime.

## Degradation mechanisms
- **Oxidation:** terpene alcohols/aldehydes → peroxides/off-odours.
- **Thermal:** esters hydrolyse; aldehydes polymerise; cis-isomers isomerise.
- **Hydrolysis:** esters + water + heat → acid + alcohol (hydrodistillation).
- **Storage:** inert atmosphere, amber glass, <15 C, minimize headspace.

## Aroma-preservation principles
1. Match method to thermo-sensitivity of target constituents.
2. Minimise residence time at high temperature.
3. SFE-CO2 for delicate florals; steam for robust herbs.
4. Pretreat gently (shade-dry, low-T, coarse comminution to limit heat).
5. Verify by GC-MS before locking parameters.