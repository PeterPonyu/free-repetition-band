# Direction 013 — entropy-controlled micro-scale test of the repeated-data value-decay law

Adjudicates a single question from Muennighoff et al., "Scaling Data-Constrained
Language Models" (NeurIPS 2023, **arXiv:2305.16264**): **is the repeated-data
decay constant R\*_D universal, or an artifact of model capacity and the
corpus's entropy-to-capacity ratio?**

A tiny decoder LM (2–10M params) is trained on **entropy-controlled synthetic
corpora**. We sweep unique-data size U against repetition epochs E at a **fixed
total token budget** B = U·E and **fixed capacity**, then fit the loss-vs-budget
surface to Muennighoff's hyperbolic effective-data form vs an exponential
alternative (InfoLaw, arXiv:2605.02364) and compare with ΔAIC/ΔBIC. A planted
canary probe measures memorization on a copied subset. If R\*_D moves with
capacity or entropy, the decay "constant" is not universal.

## Files

| file | role |
|---|---|
| `data.py` | entropy-controlled synthetic corpus generators (order-k Markov, Zipf unigram, tiny PCFG) + `measured_entropy` (plug-in conditional entropy + gzip ratio) + `make_corpus` / `epoch_loader` |
| `fitting.py` | Muennighoff hyperbolic effective-data fitter (Eq. 6) + exponential alternative + ΔAIC/ΔBIC model selection |
| `memprobe.py` | planted-canary memorization probe (canary loss vs matched fresh loss; `@no_grad` eval) |
| `train_repeat.py` | LM training loop (full-sequence next-token CE, AdamW fixed default; Muon arm subordinated) + `Config` + dynamic argparse + per-eval jsonl |
| `run_repeat.py` | the grid (NOT executed): U × epochs at fixed budget × capacity × entropy × seeds, pruned to 144 cells + fresh-data controls; resume-aware; `--dry-run` |

## Model choice

**SeqTransformer reuse** (not a fresh TinyLM). `model.py` imports the grokking
`GrokTransformer` UNMODIFIED via importlib (the grokking files are never touched)
and adds a thin `SeqTransformer` subclass whose `forward` returns full-sequence
`[B, T, vocab]` logits (grokking returns last-position only) — the same pattern
as direction 007's `induction_emergence/model.py`. The capacity axis rides on
`GrokTransformer`'s `vocab_size / d_model / n_heads / n_layers` kwargs. Capacity
presets (verified at V=256, L=128):

| preset | d_model / heads / layers | params |
|---|---|---|
| `small` | 256 / 4 / 3 | **2.53M** |
| `med`   | 384 / 6 / 3 | **5.56M** |
| `large` | 448 / 8 / 4 | **9.93M** |

(At the smoke vocab V=64, `small` is 2.40M — both ≈2M.)

## Smoke check (no files written, <60 s)
```
python data.py            # entropy-knob + gzip + determinism self-test (PASS)
python fitting.py         # decay-law fitter recovers generating form + R*/tau (PASS)
python memprobe.py        # canary/fresh bank shape self-check (PASS)
python train_repeat.py --smoke   # exact labeled smoke lines (incl. repeat probe)
python run_repeat.py --smoke     # delegates to the trainer smoke
```

The `--smoke` contract prints exactly:
```
SMOKE DATASET SHAPE: ...
SMOKE PARAM COUNT: <n>
SMOKE FORWARD LOSS: <float>
SMOKE OPTIMIZER STEP: OK
SMOKE REPEAT PROBE: entropy=<f> gzip_ratio=<f> fit_selftest=<PASS|FAIL> canary_gap=<f>
```
(≤1 step, no jsonl, exit 0; the bonus line exercises generators + fitter +
memprobe end-to-end.)

## Self-tests (what they certify)
- **`data.py`**: for each generator, turning the entropy knob low→high moves
  BOTH the measured conditional (or marginal, for PCFG) entropy AND the gzip
  ratio monotonically up; corpora are bit-identical per seed; the epoch loader
  reuses the same unique tokens faithfully every epoch.
- **`fitting.py`**: synthetic loss surfaces drawn from each form (+ noise) are
  correctly identified by the sign of ΔAIC, and the planted decay constant
  (R\*_D or τ) is recovered within tolerance.

## Dry run (prints planned cells, launches nothing)
```
python run_repeat.py --dry-run     # 144 cells (132 core + 12 fresh controls)
```
Sharding for multi-machine splits: `--num-shards N --shard-id K`.

## Real grid (run when ready — do NOT launch yet; GPU busy with 005)
```
python run_repeat.py
```
Grid: budget B=20M tokens; U-ladder {0.5,1,2,5,10,20}M with matching epochs
{40,20,10,4,2,1}; capacity {small,med,large}; entropy {low,med,high}; 3 seeds.
**Pruning** (documented in `run_repeat.py`): small+med are fully crossed
(6 U × 3 entropy × 3 seeds = 54 each); large (the ~10M-param, most expensive
arm) brackets entropy to {low,high} on a reduced 4-point U-ladder
(4 × 2 × 3 = 24). Total core = 132; + 12 fresh-data controls (E=1, U=B over
budgets {5,10,20,40}M) = **144 cells**. Results land in
`experiments/results/repeated_data/`. Resume-aware: a cell whose `.jsonl`
already ends with a `_summary` line is skipped.

## Reference
See `directions/013-repeated-data-law.md` for the full research write-up.
