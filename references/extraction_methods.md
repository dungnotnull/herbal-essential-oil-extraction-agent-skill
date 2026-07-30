# Extraction Methods Reference — Essential Oil & Aromatic Chemistry

Authoritative baseline reference used by the `core-analysis` agent and the
`yield_estimator` / `gcms_profile` tools. All ranges are literature-typical;
confirm against current sources before scale-up.

## 1. Steam distillation
- **Principle:** steam strips volatiles; condensate separates oil/water.
- **T:** ~100 C (atmospheric); **P:** ~1 bar.
- **Time:** 90–180 min depending on herb.
- **Best for:** most robust herbs (lavender, peppermint, rosemary, lemongrass, clove).
- **Risk:** thermal degradation of thermolabile compounds (aldehydes, esters).

## 2. Hydrodistillation
- **Principle:** plant immersed in boiling water; Clevenger trap.
- **T:** ~100 C; **P:** ~1 bar.
- **Best for:** hard/seedy material (e.g. clove buds, fennel).
- **Risk:** higher thermal + hydrolytic stress than steam.

## 3. Supercritical CO2 (SFE-CO2)
- **Principle:** CO2 above critical point (T>31 C, P>74 bar) acts as tunable solvent.
- **Typical:** 40–60 C, 100–300 bar.
- **Best for:** thermo-labile, high-value aromas (jasmine, delicate florals).
- **Pros:** low-T preserves aroma; selective by pressure.
- **Cons:** capex; high pressure; co-extracts waxes/cuticular lipids.

## 4. Microwave-assisted extraction (MAE)
- **Principle:** microwave heats intracellular water, ruptures glands.
- **T:** moderate; short time (10–40 min).
- **Best for:** rapid screening; lab-scale.
- **Risk:** hot-spots; non-uniform heating.

## Parameter sensitivity (qualitative)
| Parameter            | Yield effect | Aroma effect |
|---------------------|--------------|--------------|
| Temperature (up)     | + then plateau | - (degradation) |
| Pressure (SFE, up)  | + selectivity | + aroma retained |
| Time (up, saturating)| + then plateau | - if overheated |
| Plant:water ratio   | + then saturation | neutral–positive |
| Particle size (down) | + (cell rupture) | neutral |

## Standardization anchors
- ISO 4720 — essential oil nomenclature.
- ISO 4731 — individual oil specifications.
- PhEur / USP — identity, limits, adulteration tests.
- GC-MS chemotype match as primary identity check.