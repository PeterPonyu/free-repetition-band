"""Direction 013 — repeated-data law grid runner (NOT executed yet).

Core grid: at a FIXED total token budget B, sweep the unique-data size U (and
hence the matching repetition count E = B / U) against model capacity and corpus
entropy, over 3 seeds. Fitting the resulting loss-vs-budget surface to the
Muennighoff hyperbolic effective-data form vs the InfoLaw exponential
alternative (fitting.py) — and asking whether the recovered decay constant R*_D
moves with capacity / entropy — is the study's adjudication.

Budget & unique/epoch ladder (B = 20M tokens)
---------------------------------------------
    U (unique tokens) :  0.5M   1M    2M    5M    10M   20M
    E (epochs = B/U)  :  40     20    10    4     2     1
(So every cell processes the same ~20M total tokens; the axis being swept is how
many UNIQUE tokens that budget covers, i.e. how much repetition.)

Full crossing would be 6 U-ladder x 3 capacity x 3 entropy x 3 seeds = 162.
PRUNING to 132 core cells (documented):
  - capacity={small,med}: full 6 U x 3 entropy x 3 seeds = 54 each (108 cells)
    -> the capacity-vs-decay question needs both these fully crossed with entropy.
  - capacity=large (~10M params; the most expensive): drop to entropy={low,high}
    (skip 'med', the interior point) AND a reduced 4-point U-ladder that still
    spans the full repetition range -> 4 U x 2 entropy x 3 seeds = 24 cells
    -> large only has to BRACKET the entropy effect and the decay endpoints.
  total core = 108 + 24 = 132 cells; + 12 fresh controls = 144 (in 120-150).

Fresh-data controls (~12 cells)
-------------------------------
For the U=20M / E=1 column (no repetition) at every (capacity, entropy-bracket)
we already have a single-epoch point inside the core grid; the controls instead
fix U=B (so E=1, all-fresh) but vary the budget B itself over a few values to
anchor the no-repetition Chinchilla floor that the decay forms decay TOWARD.
    capacity={small,med,large} x budget B in {5M,10M,20M,40M} (E=1, entropy=med)
    = 3 x 4 = 12 fresh-data control cells.

Output: ../../experiments/results/repeated_data/<name>.jsonl
Resume-aware: a cell whose jsonl already ends with a _summary line is skipped.

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

# --- budget / unique-epoch ladder (fixed total token budget) -----------------
BUDGET = 20_000_000
U_LADDER = [500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000, 20_000_000]
# large capacity (~10M params, the most expensive arm) uses a reduced U-ladder
# that still spans the full repetition range (heavy-repeat 0.5M..light-repeat
# 20M) but drops two interior points to keep the total cell count in range.
U_LADDER_LARGE = [500_000, 2_000_000, 5_000_000, 20_000_000]
GENERATOR = "markov"
SEEDS = [0, 1, 2]

# entropy bracketing per capacity (pruning lever)
ENTROPY_FULL = ["low", "med", "high"]
ENTROPY_BRACKET = ["low", "high"]

# fresh-data control budgets (E=1, U=B; anchors the no-repeat floor)
CONTROL_BUDGETS = [5_000_000, 10_000_000, 20_000_000, 40_000_000]

OUT = os.path.join(_THIS_DIR, "..", "..", "experiments", "results",
                   "repeated_data")


def _epochs_for(U: int, budget: int = BUDGET) -> int:
    return max(1, round(budget / U))


def _tag_u(U: int) -> str:
    return f"{U/1e6:g}M".replace(".", "p")


def _core_cells():
    """Core loss-vs-budget grid cells: (name, overrides)."""
    cells = []
    cap_entropy = [
        ("small", ENTROPY_FULL,    U_LADDER),
        ("med",   ENTROPY_FULL,    U_LADDER),
        ("large", ENTROPY_BRACKET, U_LADDER_LARGE),  # pruned: bracket entropy + reduced U
    ]
    for cap, ent_levels, u_ladder in cap_entropy:
        for ent in ent_levels:
            for U in u_ladder:
                E = _epochs_for(U)
                for seed in SEEDS:
                    name = f"{cap}_{ent}_U{_tag_u(U)}_E{E}_s{seed}"
                    cells.append((name, dict(
                        capacity=cap, entropy_level=ent, generator=GENERATOR,
                        unique_tokens=U, n_epochs=E, total_budget=BUDGET,
                        seed=seed)))
    return cells


def _control_cells():
    """Fresh-data control cells (E=1, U=B): (name, overrides)."""
    cells = []
    for cap in ["small", "med", "large"]:
        for B in CONTROL_BUDGETS:
            name = f"ctrl_{cap}_fresh_B{_tag_u(B)}_s0"
            cells.append((name, dict(
                capacity=cap, entropy_level="med", generator=GENERATOR,
                unique_tokens=B, n_epochs=1, total_budget=B, seed=0)))
    return cells


def already_done(path: str) -> bool:
    """True iff the jsonl exists and ends with a _summary line."""
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
    ap = argparse.ArgumentParser(description="repeated-data law grid runner")
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

    core = _core_cells()
    controls = _control_cells()
    all_cells = core + controls
    cells = shard_cells(all_cells, args.num_shards, args.shard_id)

    if args.dry_run:
        print(f"[repeated_data] dry-run: {len(cells)} cells planned "
              f"(core={len(core)} + controls={len(controls)})"
              + shard_suffix(args.num_shards, args.shard_id,
                             len(all_cells), len(cells)))
        print(f"  budget B={BUDGET:,}; U-ladder={[f'{u/1e6:g}M' for u in U_LADDER]}; "
              f"seeds={SEEDS}")
        print(f"  capacity: small+med x entropy{ENTROPY_FULL} x full U-ladder, "
              f"large x entropy{ENTROPY_BRACKET} x reduced U-ladder"
              f"{[f'{u/1e6:g}M' for u in U_LADDER_LARGE]} (pruned)")
        for i, (name, ov) in enumerate(cells):
            print(f"  [{i+1:03d}/{len(cells)}] {name}  {ov}")
        sys.exit(0)

    # --- real training path (only when neither smoke nor dry-run set) ---
    os.makedirs(OUT, exist_ok=True)
    print(f"[repeated_data] {len(cells)} cells -> {OUT}"
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

    print("[repeated_data] DONE", flush=True)


if __name__ == "__main__":
    main()
