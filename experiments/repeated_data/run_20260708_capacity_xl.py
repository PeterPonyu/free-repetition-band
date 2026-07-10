"""Direction 013 follow-up — capacity span extension (xl/xxl) for the
repeated-data value-decay law.

run_repeat.py's core grid tops out at capacity="large" (~9.9M params). This
runner extends the capacity axis upward using two new additive presets in
model.py's CAPACITY_PRESETS ("xl": d_model=640/n_heads=8/n_layers=6, ~29.9M
params; "xxl": d_model=768/n_heads=8/n_layers=8, ~57.1M params, both at the
study's default vocab=256/seq_len=128 — exact counts verified via
count_params() in this file's --dry-run/--smoke path and reported below),
asking whether the decay-constant-vs-capacity trend measured across
{small,med,large} continues at much larger capacity.

Grid (B = 20M tokens fixed total budget; unique_tokens U = B / n_epochs)
-------------------------------------------------------------------------
    n_epochs (E) :  2     4     10    20
    U (unique)   :  10M   5M    2M    1M
capacity=xl  x entropy{low,med,high} x n_epochs-ladder x 3 seeds = 3x4x3 = 36
capacity=xxl x entropy=med            x n_epochs-ladder x 2 seeds = 1x4x2 = 8
total = 44 cells. generator=markov, optimizer=adamw (run_repeat.py defaults).

Output: ../../experiments/results/repeated_data_capxl/<name>.jsonl
Resume-aware: a cell whose jsonl already ends with a _summary line is skipped
(same convention as run_repeat.py).

Flags
-----
--smoke   : delegate to train_repeat smoke (no files, <60s) and exit 0.
--dry-run : print planned cells + count (incl. xl/xxl param counts) and exit 0.
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
from model import build_lm, count_params, CAPACITY_PRESETS  # noqa: E402
from runner_utils import (  # noqa: E402
    add_shard_args, shard_cells, shard_suffix, validate_shard_args,
)

# --- fixed-budget epoch ladder (capacity-span extension) ---------------------
BUDGET = 20_000_000
N_EPOCHS_LADDER = [2, 4, 10, 20]
GENERATOR = "markov"
SEEDS_XL = [0, 1, 2]
SEEDS_XXL = [0, 1]
ENTROPY_FULL = ["low", "med", "high"]

OUT = os.path.join(_THIS_DIR, "..", "..", "experiments", "results",
                   "repeated_data_capxl")


def _tag_u(U: int) -> str:
    return f"{U/1e6:g}M".replace(".", "p")


def _xl_param_counts() -> dict:
    """Instantiate xl/xxl at the study default (vocab=256, seq_len=128)."""
    out = {}
    for cap in ("xl", "xxl"):
        m = build_lm(vocab_size=256, seq_len=128, capacity=cap,
                     mlp_ratio=4, init_scale=1.0, device="cpu")
        out[cap] = count_params(m)
    return out


def _cells():
    """(name, overrides) list: xl x entropy x epoch-ladder x 3 seeds, plus
    xxl x entropy=med x epoch-ladder x 2 seeds."""
    cells = []
    for ent in ENTROPY_FULL:
        for n in N_EPOCHS_LADDER:
            U = BUDGET // n
            for seed in SEEDS_XL:
                name = f"xl_{ent}_U{_tag_u(U)}_E{n}_s{seed}"
                cells.append((name, dict(
                    capacity="xl", entropy_level=ent, generator=GENERATOR,
                    unique_tokens=U, n_epochs=n, total_budget=BUDGET,
                    seed=seed)))
    for n in N_EPOCHS_LADDER:
        U = BUDGET // n
        for seed in SEEDS_XXL:
            name = f"xxl_med_U{_tag_u(U)}_E{n}_s{seed}"
            cells.append((name, dict(
                capacity="xxl", entropy_level="med", generator=GENERATOR,
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


def main():
    ap = argparse.ArgumentParser(description="repeated-data capacity-xl grid runner")
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
        counts = _xl_param_counts()
        print(f"[repeated_data_capxl] dry-run: {len(cells)} cells planned"
              + shard_suffix(args.num_shards, args.shard_id,
                             len(all_cells), len(cells)))
        print(f"  budget B={BUDGET:,}; n_epochs-ladder={N_EPOCHS_LADDER}; "
              f"generator={GENERATOR}; entropy(xl)={ENTROPY_FULL}")
        print(f"  xl  preset={CAPACITY_PRESETS['xl']}  "
              f"n_params={counts['xl']:,} ({counts['xl']/1e6:.2f}M)  seeds={SEEDS_XL}")
        print(f"  xxl preset={CAPACITY_PRESETS['xxl']}  "
              f"n_params={counts['xxl']:,} ({counts['xxl']/1e6:.2f}M)  seeds={SEEDS_XXL}")
        for i, (name, ov) in enumerate(cells):
            print(f"  [{i+1:03d}/{len(cells)}] {name}  {ov}")
        sys.exit(0)

    # --- real training path (only when neither smoke nor dry-run set) ---
    os.makedirs(OUT, exist_ok=True)
    print(f"[repeated_data_capxl] {len(cells)} cells -> {OUT}"
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

    print("[repeated_data_capxl] DONE", flush=True)


if __name__ == "__main__":
    main()
