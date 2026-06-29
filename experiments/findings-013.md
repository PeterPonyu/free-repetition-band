# Findings 013 — The "4 epochs free" repetition constant reproduces at ~1000× smaller scale and is NOT a capacity/entropy artifact

> **Record refreshed 2026-06-29** to match the completed grid that the manuscript
> reports (the large-capacity U-ladder was filled after the original 2026-06-13
> write-up). Run count 144→177, coincidence 7/8→8/9, and the large-capacity row is
> now a full ladder (the prior "large/med has no repetition run" caveat is closed).

**Direction:** `directions/013-repeated-data-law.md` (bank OG3b 7.8; the repo's
**first language-modeling-objective** direction — full-sequence next-token loss
on synthetic Markov corpora with construction-tunable entropy).
**Question:** is Muennighoff's repetition-decay constant R*_D ≈ 4 epochs a
universal property, or an artifact of the model-capacity / data-entropy ratio?
**Data:** `results/repeated_data{,_ultragoal_large,_ultragoal_seed_audit}/` — 177 runs
(the large-capacity U-ladder, previously partial, is now fully covered; manifest
`repeated_data_ultragoal_large/manifest.json`). Core sweep at fixed token budget
B=20M: unique-tokens U swept so n_epochs = B/U ∈ {1,2,4,10,20,40}, across
capacity {small, med, large} × entropy {low, med, high}, AdamW, 3 seeds; plus
fresh-budget controls {5M,10M,40M} and a small-capacity-boundary seed audit.
Probes: held-out val loss + copied-canary memorization gap. Operationalization:
excess(n)=val_loss(n)−val_loss(fresh); R_free = largest n with median excess
< 0.05 nats (the "free epochs"). Sequence length 128, vocab 256, first-order Markov.

## Headline

On tiny synthetic Markov LMs — ~1000× below LLM scale (parameter count; the token
budget is ~45,000× smaller) — repetition is **nearly free up to ≈4 epochs and then
degrades sharply**, near Muennighoff's R*_D≈4. The threshold is **stable across the
full tested entropy range and all three capacities** (it does *not* shift ~100× as
the capacity/entropy-artifact hypothesis predicted; the observed range is a 4–10
free-epoch band, threshold-sensitive at the 0.0002-nat margin), and its onset
**coincides with the onset of memorization** (canary gap) in 8 of 9 cells. The
~100× artifact prediction is cleanly refuted; the exact 4-epoch value is not
universal in the small-capacity corner.

## P1 — Universality across scale: **REPRODUCED**

At every cell, excess val-loss stays < 0.05 nats through n=4 and rises steeply by
n=10 (e.g. med/med: 1.764→1.767→1.778 for n=1,2,4, then 1.900→3.409→5.671 for
n=10,20,40). R_free = 4 epochs in most cells; two small-capacity cells extend to
R_free=10 (excess 0.0498, just under the 0.05 threshold). The "~4 epochs free"
constant — fitted by Muennighoff et al. at LLM scale on natural language —
reproduces on a 2–10M-param Markov LM. No Charton-Kempe double-descent appeared
(excess is monotone in n; the non-monotone-decay falsifier did not fire).

> Read-team note (refreshed 2026-06-29): "universality" here = **stable across the
> TESTED capacity/entropy range** (R_free 4–10, ≤2.5×, NOT the predicted ~100× shift).
> The large-capacity U-ladder is now fully covered (closing the prior gap), so the
> capacity axis is no longer carried by small-vs-med alone. The strong, surviving
> claim is the refutation of the ~100× artifact prediction; the 4–10 band itself is
> threshold-sensitive and carries no CI/p-value on R_free.

## P2 (headline) — Capacity/entropy artifact: **FALSIFIED → universality confirmed (clean negative)**

| | low | med | high |
|---|---|---|---|
| small | R_free=10 | R_free=10 | R_free=4 |
| med | R_free=4 | R_free=4 | R_free=4 |
| large | R_free=4 | R_free=4 | R_free=4 |

Sweeping entropy across its full constructed range (val-loss floor 0.37→1.76→4.10
nats for low/med/high — a >10× entropy span) leaves R_free pinned at ≈4 epochs.
The artifact hypothesis predicted a ~100× systematic shift of R*_D with the
capacity/entropy ratio; **the observed range is 4–10 epochs (≤2.5×), with no
monotone trend in entropy**. The only modulation is mild and capacity-side:
small-capacity models tolerate slightly more repetition (R_free 10 at low/med
entropy) — plausibly because a smaller model memorizes the unique set more
slowly. This is the preregistered "P2-falsified = cross-distribution
universality confirmation" branch: R*_D is **not** a setting artifact at this
scale. The falsification is strongest along the **entropy** axis (>10× span, fully
covered); the capacity span is only ~4×.

## P3 — Memorization coupling: **CONFIRMED (8/9 cells), not a sampling artifact**

The copied-canary gap stays ≈0 (often slightly negative) through n=4 and rises
in lockstep with the val-loss degradation: decay_onset == mem_onset in 8 of 9
cells. The single mismatch (small/low: memorization onset at 10 slightly precedes
decay at 20) is in the most repetition-tolerant cell. Because the **fresh-data
control shares the identical sampling scheme** yet shows canary≈0 throughout, the
memorization-locked onset cannot be the sampling-bias artifact of 2605.20314:
"repetition gets expensive exactly when the model begins memorizing the unique
set" survives that dissociation. (Observational coincidence, not a causal proof.)

## P4 — Hyperbolic vs exponential decay form: **not decidable at this resolution**

The n-ladder {1,2,4,10,20,40} is too coarse (and the pre-onset region too flat)
for a ΔAIC>10 discrimination between the hyperbolic (2305.16264) and exponential
(2605.02364) families — the informative region is a single steep rise between
n=4 and n=20. Reported as indistinguishable here; a denser ladder (n=4..16 by 2)
would be needed. P4 was preregistered as strictly subordinate; no optimizer arm run.

## Limitations

- The 4–10 free-epoch band rests on a 0.0002-nat margin (two small-capacity cells
  at excess 0.0498 vs the 0.05 threshold); at ε_free=0.045 it collapses to the
  4-epoch constant, at 0.10 it expands. No CI/p-value is attached to R_free.
- Synthetic Markov corpora only (one generator family); entropy tuned by
  construction — natural-language entropy structure is richer (real-text bridge in
  `results/repeated_data_realtext/` partially addresses this).
- R_free is a 0.05-nat threshold on a coarse n-grid; the true R*_D is bracketed
  to (4, 10) for most cells, not point-fitted.
- AdamW only, one seq-len/vocab; canary probe is a copied-subset gap.

## Figures / data

`results/figures-013/`: `fig_repeat.png` (excess-loss decay + canary onset, with
the R*_D≈4 reference line), `repeat_verdicts.json` (per-cell excess/canary
curves, R_free, decay/mem onsets, P2/P3 tallies). Large-row manifest:
`results/repeated_data_ultragoal_large/manifest.json`. Real-text bridge:
`results/repeated_data_realtext/`.
