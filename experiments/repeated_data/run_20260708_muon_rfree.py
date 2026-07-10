"""Direction 013 follow-up — Muon optimizer generality check for the
repeated-data value-decay law (R_free).

run_repeat.py's core grid fixes AdamW as the (deliberately) sole optimizer.
train_repeat.py already supports a subordinated `optimizer="muon"` arm (Muon
on 2-D hidden matrices via the grokking name-based split + AdamW on the rest;
see train_repeat.build_optimizer). This runner reuses that arm unmodified to
ask whether the repetition-value-decay law (and its R_free onset) is
optimizer-specific or survives under Muon.

Grid (B = 20M tokens fixed total budget; unique_tokens U = B / n_epochs)
-------------------------------------------------------------------------
    n_epochs (E) :  1     2     4     10    20    40
    U (unique)   :  20M   10M   5M    2M    1M    0.5M
optimizer=muon x capacity{small,med} x entropy="med" x generator=markov
x n_epochs-ladder x 3 seeds = 2 x 6 x 3 = 36 cells.

Output: ../../experiments/results/repeated_data_muon/<name>.jsonl
Resume-aware: a cell whose jsonl already ends with a _summary line is skipped
(same convention as run_repeat.py).

Flags
-----
--smoke   : delegate to train_repeat smoke (no files, <60s) and exit 0.
--dry-run : print planned cells and exit 0 (launches NOTHING).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
_EXPERIMENTS_DIR = os.path.dirname(_THIS_DIR)
if _EXPERIMENTS_DIR not in sys.path:
    sys.path.append(_EXPERIMENTS_DIR)

from train_repeat import Config, run, run_smoke  # noqa: E402
from runner_utils import (  # noqa: E402
    add_shard_args, shard_cells, shard_suffix, validate_shard_args,
)

# --- fixed-budget epoch ladder (Muon optimizer arm; entropy fixed at 'med') --
BUDGET = 20_000_000
N_EPOCHS_LADDER = [1, 2, 4, 10, 20, 40]
GENERATOR = "markov"
ENTROPY_LEVEL = "med"
CAPACITIES = ["small", "med"]
SEEDS = [0, 1, 2]
OPTIMIZER = "muon"

OUT = os.path.join(_THIS_DIR, "..", "..", "experiments", "results",
                   "repeated_data_muon")


def _tag_u(U: int) -> str:
    return f"{U/1e6:g}M".replace(".", "p")


def _cells():
    """(name, overrides) list: capacity x n_epochs-ladder x seeds."""
    cells = []
    for cap in CAPACITIES:
        for n in N_EPOCHS_LADDER:
            U = BUDGET // n
            for seed in SEEDS:
                name = f"{cap}_muon_U{_tag_u(U)}_E{n}_s{seed}"
                cells.append((name, dict(
                    capacity=cap, entropy_level=ENTROPY_LEVEL, generator=GENERATOR,
                    unique_tokens=U, n_epochs=n, total_budget=BUDGET,
                    optimizer=OPTIMIZER, seed=seed)))
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


def main():
    ap = argparse.ArgumentParser(description="repeated-data Muon grid runner")
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
        print(f"[repeated_data_muon] dry-run: {len(cells)} cells planned"
              + shard_suffix(args.num_shards, args.shard_id,
                             len(all_cells), len(cells)))
        print(f"  budget B={BUDGET:,}; n_epochs-ladder={N_EPOCHS_LADDER}; "
              f"seeds={SEEDS}; optimizer={OPTIMIZER}; generator={GENERATOR}; "
              f"entropy_level={ENTROPY_LEVEL}; capacities={CAPACITIES}")
        for i, (name, ov) in enumerate(cells):
            print(f"  [{i+1:03d}/{len(cells)}] {name}  {ov}")
        sys.exit(0)

    # --- real training path (only when neither smoke nor dry-run set) ---
    os.makedirs(OUT, exist_ok=True)
    print(f"[repeated_data_muon] {len(cells)} cells -> {OUT}"
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
        print(f"[{i+1}/{len(cells)}] {name}: "
              f"val={s['final_val_loss']:.3f} "
              f"canary_gap={s['final_canary_gap']:.3f} "
              f"({time.time()-t0:.0f}s)", flush=True)

    print("[repeated_data_muon] DONE", flush=True)


if __name__ == "__main__":
    main()
