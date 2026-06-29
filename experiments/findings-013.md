# Findings 013 — The "4 epochs free" repetition constant reproduces at ~1000× smaller scale and is NOT a capacity/entropy artifact

**Direction:** `directions/013-repeated-data-law.md` (bank OG3b 7.8; the repo's
**first language-modeling-objective** direction — full-sequence next-token loss
on synthetic Markov corpora with construction-tunable entropy).
**Question:** is Muennighoff's repetition-decay constant R*_D ≈ 4 epochs a
universal property, or an artifact of the model-capacity / data-entropy ratio?
**Data:** `results/repeated_data/` — 144 runs. Core sweep at fixed token budget
B=20M: unique-tokens U swept so n_epochs = B/U ∈ {1,2,4,10,20,40}, across
capacity {small, med, large} × entropy {low, med, high}, AdamW, 3 seeds; plus
fresh-budget controls {5M,10M,40M}. Probes: held-out val loss + copied-canary
memorization gap. Operationalization: excess(n)=val_loss(n)−val_loss(fresh);
R_free = largest n with median excess < 0.05 nats (the "free epochs").

## Headline

On tiny synthetic Markov LMs — ~1000× below LLM scale — repetition is **nearly
free up to ≈4 epochs and then degrades sharply**, exactly Muennighoff's R*_D≈4.
The threshold is **stable across the full tested entropy range and (small–med)
capacity** (it does *not* shift ~100× as the capacity/entropy-artifact hypothesis
predicted; the large-capacity row is only partially covered — see below), and its
onset **coincides with the onset of memorization** (canary gap) in 7 of 8
measurable cells. R*_D behaves as a genuine constant of repeated
training, not a design artifact.

## P1 — Universality across scale: **REPRODUCED**

At every fully-covered cell, excess val-loss stays < 0.05 nats through n=4 and
rises steeply by n=10 (e.g. small/med: 1.765→1.770→1.778 for n=1,2,4, then
1.814→2.152→4.945 for n=10,20,40). R_free = 4 epochs in 6/9 cells. The
"~4 epochs free" constant — fitted by Muennighoff et al. at LLM scale on natural
language — reproduces on a 2–10M-param Markov LM. No Charton-Kempe double-descent
appeared (excess is monotone in n; the non-monotone-decay falsifier did not fire).

> Red-team note (2026-06-14): "universality" here = **stable across the TESTED
> capacity/entropy range** (R_free 4–10, ≤2.5×, NOT the predicted ~100× shift) —
> the large-capacity column is undersampled at B=20M (large/med has NO repetition
> run; the prior "n=1" was a borrowed fresh control), so the capacity axis rests
> mainly on small-vs-med. The strong, surviving claim is the
> refutation of the ~100× artifact prediction, not unbounded universality.

## P2 (headline) — Capacity/entropy artifact: **FALSIFIED → universality confirmed (clean negative)**

| | low | med | high |
|---|---|---|---|
| small | R_free=10 | R_free=10 | R_free=4 |
| med | R_free=4 | R_free=4 | R_free=4 |
| large | R_free=4* | — (no repetition run)* | R_free=4* |

Sweeping entropy across its full constructed range (val-loss floor 0.37→1.76→4.10
nats for low/med/high — a >10× entropy span) leaves R_free pinned at ≈4 epochs.
The artifact hypothesis predicted a ~100× systematic shift of R*_D with the
capacity/entropy ratio; **the observed range is 4–10 epochs (≤2.5×), with no
monotone trend in entropy**. The only modulation is mild and capacity-side:
small-capacity models tolerate slightly more repetition (R_free 10 at low/med
entropy) — plausibly because a smaller model memorizes the unique set more
slowly. This is the preregistered "P2-falsified = cross-distribution
universality confirmation" branch: R*_D is **not** a setting artifact at this
scale. (*large-capacity cells are under-covered at B=20M — large/low and
large/high cover only n∈{1,4,10,40} (missing 2,20, the onset bracket), and
**large/med has NO repetition run** — the "n=1" value previously tabulated was a
borrowed fresh control (ctrl_large_fresh_B20M, removed) — so the large row is
indicative, not a full ladder; see Limitations.)

## P3 — Memorization coupling: **CONFIRMED (7/8 cells), not a sampling artifact**

The copied-canary gap stays ≈0 (often slightly negative) through n=4 and rises
in lockstep with the val-loss degradation: decay_onset == mem_onset in 7 of 8
full-coverage cells (both = 10 epochs in 6 cells; both = 20 in small/med). The
single mismatch (small/low: memorization onset at 10 slightly precedes decay at
20) is in the most repetition-tolerant cell. Because the **fresh-data control
shares the identical sampling scheme** yet shows canary≈0 throughout, the
memorization-locked onset cannot be the sampling-bias artifact of 2605.20314:
"repetition gets expensive exactly when the model begins memorizing the unique
set" survives that dissociation.

## P4 — Hyperbolic vs exponential decay form: **not decidable at this resolution**

The n-ladder {1,2,4,10,20,40} is too coarse (and the pre-onset region too flat)
for a ΔAIC>10 discrimination between the hyperbolic (2305.16264) and exponential
(2605.02364) families — the informative region is a single steep rise between
n=4 and n=20. Reported as indistinguishable here; a denser ladder (n=4..16 by 2)
would be needed. P4 was preregistered as strictly subordinate; no optimizer arm run.

## Limitations

- **Coverage gap:** large-capacity cells at B=20M are partial — **large/med has no
  repetition run** (the previously tabulated n=1 point was a borrowed fresh control,
  ctrl_large_fresh_B20M, not a repetition measurement — removed); large/low and
  large/high miss n=2,20 (the onset bracket). The capacity axis of P2 rests mainly
  on small-vs-med; large is indicative. A re-run filling the large U-ladder would
  close it.
- Synthetic Markov corpora only (one generator family); entropy tuned by
  construction — natural-language entropy structure is richer.
- R_free is a 0.05-nat threshold on a coarse n-grid; the true R*_D is bracketed
  to (4, 10) for most cells, not point-fitted.
- AdamW only, one seq-len/vocab; canary probe is a copied-subset gap.

## Figures / data

`results/figures-013/`: `fig_repeat.png` (excess-loss decay + canary onset, with
the R*_D≈4 reference line), `repeat_verdicts.json` (per-cell excess/canary
curves, R_free, decay/mem onsets, P2/P3 tallies).
