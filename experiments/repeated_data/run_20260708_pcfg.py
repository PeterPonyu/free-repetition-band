"""Direction 013 follow-up — PCFG (non-Markov) corpus family for the
repeated-data value-decay law.

run_repeat.py's core grid uses the order-k Markov generator exclusively. This
runner asks whether the repetition-value-decay law is generator-specific by
rerunning the same fixed-budget epoch ladder on `data.py`'s tiny PCFG
generator (`generator="pcfg"`, knob `pcfg_ambiguity`) instead.

Grid (B = 20M tokens fixed total budget; unique_tokens U = B / n_epochs)
-------------------------------------------------------------------------
    n_epochs (E) :  1     2     4     10    20    40
    U (unique)   :  20M   10M   5M    2M    1M    0.5M
capacity {small, med, large} x n_epochs-ladder x 3 seeds = 3 x 6 x 3 = 54 cells.

Entropy handling: the PCFG generator's only entropy knob is
`pcfg_ambiguity` (data.py's `knobs_for_level` table: low=0.02, med=0.25,
high=1.0). This runner fixes entropy_level="med" (the generator's default /
mid setting) for every cell — entropy is NOT swept here (that axis is owned
by run_repeat.py's Markov grid) — and instead RECORDS the empirical
`measured_entropy` (data.py) of each cell's corpus into the jsonl as a
`_pcfg_entropy` record, analogous to how run_repeat.py's smoke path reports
measured_entropy for its corpus. The witness is computed on a bounded
deterministic PREFIX of the cell's actual corpus (data.py's generators draw
their random stream sequentially, so a short prefix is bit-identical to the
start of the full corpus) to keep the O(U) plug-in entropy estimator cheap
even at U=20M.

Output: ../../experiments/results/repeated_data_pcfg/<name>.jsonl
Resume-aware: a cell whose jsonl already ends with a _summary line is skipped
(same convention as run_repeat.py; the post-hoc `_pcfg_entropy` line is always
appended right after `_summary` so it stays within the resume-check's tail
window).

Flags
-----
--smoke   : delegate to train_repeat smoke (no files, <60s) and exit 0.
--dry-run : print planned cells and exit 0 (launches NOTHING).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
_EXPERIMENTS_DIR = os.path.dirname(_THIS_DIR)
if _EXPERIMENTS_DIR not in sys.path:
    sys.path.append(_EXPERIMENTS_DIR)

from train_repeat import Config, run, run_smoke, make_knobs  # noqa: E402
from data import make_corpus, measured_entropy  # noqa: E402
from runner_utils import (  # noqa: E402
    add_shard_args, shard_cells, shard_suffix, validate_shard_args,
)

# --- fixed-budget epoch ladder (PCFG generator; entropy fixed at 'med') ------
BUDGET = 20_000_000
N_EPOCHS_LADDER = [1, 2, 4, 10, 20, 40]
GENERATOR = "pcfg"
ENTROPY_LEVEL = "med"          # the generator's default/mid pcfg_ambiguity setting
CAPACITIES = ["small", "med", "large"]
SEEDS = [0, 1, 2]

# entropy-witness probe: bounded prefix length for the plug-in estimator/gzip
# (deterministic prefix of the real corpus; keeps the O(U) estimator cheap).
ENTROPY_PROBE_TOKENS = 20_000

OUT = os.path.join(_THIS_DIR, "..", "..", "experiments", "results",
                   "repeated_data_pcfg")


def _tag_u(U: int) -> str:
    return f"{U/1e6:g}M".replace(".", "p")


def _cells():
    """(name, overrides) list: capacity x n_epochs-ladder x seeds."""
    cells = []
    for cap in CAPACITIES:
        for n in N_EPOCHS_LADDER:
            U = BUDGET // n
            for seed in SEEDS:
                name = f"{cap}_pcfg_U{_tag_u(U)}_E{n}_s{seed}"
                cells.append((name, dict(
                    capacity=cap, entropy_level=ENTROPY_LEVEL, generator=GENERATOR,
                    unique_tokens=U, n_epochs=n, total_budget=BUDGET,
                    seed=seed)))
    return cells


def already_done(path: str) -> bool:
    """True iff the jsonl exists and ends with a _summary line (in its tail)."""
    if not os.path.exists(path):
        return False
    with open(path, "rb") as fh:
        fh.seek(0, 2)
        size = fh.tell()
        if size == 0:
            return False
        fh.seek(max(0, size - 4096))
        tail = fh.read().decode("utf-8", errors="replace")
    return '"_summary"' in tail


def _record_pcfg_entropy(cfg: Config, path: str) -> dict:
    """Append a _pcfg_entropy witness line (bounded-prefix probe) to the jsonl."""
    knobs = make_knobs(cfg)
    probe_n = min(cfg.unique_tokens, ENTROPY_PROBE_TOKENS)
    probe_corpus = make_corpus(probe_n, knobs, seed=cfg.seed)
    m = measured_entropy(probe_corpus, cond_order=1)
    rec = {"_pcfg_entropy": {
        "probe_tokens": probe_n,
        "pcfg_ambiguity": knobs.pcfg_ambiguity,
        "cond_entropy_bits": m["cond_entropy_bits"],
        "marginal_entropy_bits": m["marginal_entropy_bits"],
        "gzip_ratio": m["gzip_ratio"],
    }}
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec["_pcfg_entropy"]


def main():
    ap = argparse.ArgumentParser(description="repeated-data PCFG grid runner")
    ap.add_argument("--smoke", action="store_true",
                    help="Run smoke checks and exit (no files written)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print planned cells and exit (no training)")
    add_shard_args(ap)
    args = ap.parse_args()
    validate_shard_args(args)

    if args.smoke:
        run_smoke()
        sys.exit(0)

    all_cells = _cells()
    cells = shard_cells(all_cells, args.num_shards, args.shard_id)

    if args.dry_run:
        print(f"[repeated_data_pcfg] dry-run: {len(cells)} cells planned"
              + shard_suffix(args.num_shards, args.shard_id,
                             len(all_cells), len(cells)))
        print(f"  budget B={BUDGET:,}; n_epochs-ladder={N_EPOCHS_LADDER}; "
              f"seeds={SEEDS}; generator={GENERATOR}; entropy_level={ENTROPY_LEVEL}")
        for i, (name, ov) in enumerate(cells):
            print(f"  [{i+1:03d}/{len(cells)}] {name}  {ov}")
        sys.exit(0)

    # --- real training path (only when neither smoke nor dry-run set) ---
    os.makedirs(OUT, exist_ok=True)
    print(f"[repeated_data_pcfg] {len(cells)} cells -> {OUT}"
          + shard_suffix(args.num_shards, args.shard_id,
                         len(all_cells), len(cells)), flush=True)

    for i, (name, ov) in enumerate(cells):
        path = os.path.join(OUT, name + ".jsonl")
        if already_done(path):
            print(f"[{i+1}/{len(cells)}] skip {name}", flush=True)
            continue
        cfg = Config(**ov)
        t0 = time.time()
        s, _ = run(cfg, out_path=path)
        ent = _record_pcfg_entropy(cfg, path)
        print(f"[{i+1}/{len(cells)}] {name}: "
              f"val={s['final_val_loss']:.3f} "
              f"canary_gap={s['final_canary_gap']:.3f} "
              f"cond_entropy={ent['cond_entropy_bits']:.3f} "
              f"gzip={ent['gzip_ratio']:.3f} "
              f"({time.time()-t0:.0f}s)", flush=True)

    print("[repeated_data_pcfg] DONE", flush=True)


if __name__ == "__main__":
    main()
