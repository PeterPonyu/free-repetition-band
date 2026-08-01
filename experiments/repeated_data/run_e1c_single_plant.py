"""E1-C — exposure-matched canary control for the memorization-onset ordering.

Why this arm exists
-------------------
Every published E1 canary measurement plants each canary 4x into the unique
pool (memprobe.plant_canaries(n_repeats=4), the Config default), so at epoch
count n a canary has received 4n gradient exposures while an ordinary corpus
token has received n. The headline ordering — memorization onset LEADS OR
COINCIDES WITH, and never lags, decay onset — is therefore read off a probe
that is 4x oversampled relative to the data whose decay it is being compared
against. On an exposure-matched axis the ordering inverts in 9/9 cells.

This arm plants each canary EXACTLY ONCE per pool (canary_repeats=1), so canary
exposures equal the epoch count and the two onsets live on the same axis. The
canary_repeats=4 arm is run at the SAME fresh seeds as an internal replication
of the published convention, so the comparison is within-arm rather than
against archived runs that differ in seed block.

Grid
----
Core synthetic grid of the published E1 result (run_repeat.py conventions):
B = 20M tokens fixed, U = B/n, generator=markov, seq_len 128, batch 32,
AdamW lr 3e-4 wd 0.01 betas 0.9/0.98, val_batches 4 (harness default — the
val_batches=16 deviation belongs to the real-text S-E1 round, not here).

    capacity     : small (2.5M) | med (5.6M) | large (9.9M)
    entropy      : low | med | high                       -> 9 cells
    n_epochs     : 1, 2, 4, 10, 20, 40   (the published U-ladder)
    canary_repeats: 1 (exposure-matched, NEW) | 4 (published convention)
    seeds        : 201, 202, 203  (fresh block; see SEEDS note below)
  9 cells x 6 rungs x 2 plant rates x 3 seeds = 324 runs.

SEEDS: the synthetic E1 family has used seeds 0-14 (results/repeated_data*,
including the 15-seed ultragoal seed audit) and the real-text S-E1 round used
50-51. The 201-203 block is disjoint from both. The seed drives the corpus, the
canary bank (900M+seed), the fresh bank (910M+seed) and the val stream
(500M+seed), so a fresh block gives fresh data as well as fresh init.

Readout (analyze_e1c.py): per cell and plant rate, decay onset (first grid n
with excess >= 0.05 nats vs that arm's own n=1) and canary memorization onset
(first grid n with gap >= 0.10 nats), the leads/coincides/lags verdict, and
both onsets restated in EXPOSURE units (canary exposures = n * canary_repeats,
corpus exposures = n).

Output: experiments/revision2026/gpu2026/e1c/<name>.jsonl (+ MANIFEST.json).
Resume-safe: a cell whose jsonl already ends with a _summary line is skipped.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
_EXPERIMENTS_DIR = os.path.dirname(_THIS_DIR)
if _EXPERIMENTS_DIR not in sys.path:
    sys.path.append(_EXPERIMENTS_DIR)

import e1_gpu_common as G  # noqa: E402

G.preselect_gpu()  # must precede the first torch import (via train_repeat)

from train_repeat import Config, run  # noqa: E402
from runner_utils import (  # noqa: E402
    add_shard_args, shard_cells, shard_suffix, validate_shard_args,
)

ARM = "e1c"
BUDGET = 20_000_000
N_LADDER = [1, 2, 4, 10, 20, 40]
PLANT_RATES = [1, 4]
CAPS = ["small", "med", "large"]
ENTS = ["low", "med", "high"]
GENERATOR = "markov"
SEEDS = [201, 202, 203]
PILOT_CELL = ("med", "med")

SEQ_LEN = Config.seq_len
BATCH_SIZE = Config.batch_size
N_CANARY = Config.n_canary

OUT = os.path.join(_EXPERIMENTS_DIR, "revision2026", "gpu2026", ARM)


def _cells():
    """(name, overrides) for the full 324-run grid, in queue order."""
    cells = []
    for cap in CAPS:
        for ent in ENTS:
            for nrep in PLANT_RATES:
                for n in N_LADDER:
                    U = BUDGET // n
                    for seed in SEEDS:
                        name = f"e1c_{cap}_{ent}_r{nrep}_E{n}_s{seed}"
                        cells.append((name, dict(
                            capacity=cap, entropy_level=ent,
                            generator=GENERATOR, unique_tokens=U, n_epochs=n,
                            total_budget=BUDGET, canary_repeats=nrep,
                            seed=seed)))
    return cells


def _pilot_cells(cells):
    cap, ent = PILOT_CELL
    return [(name, ov) for name, ov in cells
            if ov["capacity"] == cap and ov["entropy_level"] == ent
            and ov["seed"] == SEEDS[0]]


def _eta_rows(cells):
    """Per-capacity (runs, fast-hours, slow-hours) using the ETA.md law."""
    rows = {}
    params = {cap: G.param_count(cap, Config.vocab, SEQ_LEN) for cap in CAPS}
    for _, ov in cells:
        cap = ov["capacity"]
        toks = G.tokens_per_run(ov["unique_tokens"], ov["n_epochs"], SEQ_LEN,
                                BATCH_SIZE, N_CANARY, ov["canary_repeats"])
        fast, slow = G.est_tok_per_s(params[cap], BATCH_SIZE * SEQ_LEN)
        r = rows.setdefault(cap, [0, 0.0, 0.0])
        r[0] += 1
        r[1] += G.run_hours(toks, fast)
        r[2] += G.run_hours(toks, slow)
    return params, rows


def _dry_run(cells, all_cells, args):
    params, rows = _eta_rows(cells)
    print(f"[{ARM}] dry-run: {len(cells)} cells planned"
          + shard_suffix(args.num_shards, args.shard_id, len(all_cells),
                         len(cells)))
    print(f"  budget B={BUDGET:,}; n-ladder={N_LADDER}; plant rates="
          f"{PLANT_RATES}; capacities={CAPS}; entropy={ENTS}; seeds={SEEDS}")
    print(f"  protocol: generator={GENERATOR} seq_len={SEQ_LEN} "
          f"batch={BATCH_SIZE} adamw lr={Config.lr} wd={Config.weight_decay} "
          f"val_batches={Config.val_batches} n_canary={N_CANARY}")
    print(f"  throughput law: tok/s = {G.LAW_COEF:.3e} * params^-{G.LAW_EXP:.3f} "
          f"(fit to ETA.md anchors; ceiling {G.CEILING_STEPS_PER_S:.0f} steps/s)")
    for p, meas, pred in G.anchor_residuals():
        print(f"    anchor {p/1e6:6.1f}M params: measured {meas:>9,.0f} tok/s, "
              f"law {pred:>9,.0f} tok/s ({100*(pred-meas)/meas:+.1f}%)")
    tot_f = tot_s = 0.0
    for cap in CAPS:
        if cap not in rows:
            continue
        n, hf, hs = rows[cap]
        fast, slow = G.est_tok_per_s(params[cap], BATCH_SIZE * SEQ_LEN)
        print(G.format_eta(f"{cap} ({params[cap]/1e6:.2f}M, "
                           f"{slow/1e3:.0f}-{fast/1e3:.0f}k tok/s)", n, hf, hs))
        tot_f += hf
        tot_s += hs
    lo, hi = G.GPU4090_SPEEDUP
    print(G.format_eta("TOTAL", len(cells), tot_f, tot_s))
    print(f"  (4080-SUPER-equivalent; a 4090 is ~{lo}-{hi}x faster on this "
          f"fp32 workload. Anchors are seq_len 256, these runs are seq_len 128.)")
    for i, (name, ov) in enumerate(cells):
        print(f"  [{i+1:03d}/{len(cells)}] {name}  {ov}")


def _smoke():
    """CPU end-to-end: tiny cells through train_repeat.run + the real readout."""
    from analyze_e1c import load_summaries, build_verdict, render_table

    threads = G.limit_cpu_threads()
    t0 = time.time()
    tmp = tempfile.mkdtemp(prefix="e1c_smoke_")
    tiny = dict(unique_tokens=6144, seq_len=32, batch_size=8, vocab=64,
                capacity="small", entropy_level="med", generator=GENERATOR,
                n_canary=4, val_batches=2, total_budget=6144, device="cpu")
    cells = []
    for nrep in PLANT_RATES:
        for n in (1, 2):
            name = f"e1c_small_med_r{nrep}_E{n}_s{SEEDS[0]}"
            cells.append((name, dict(tiny, n_epochs=n, canary_repeats=nrep,
                                     seed=SEEDS[0])))
    for name, ov in cells:
        path = os.path.join(tmp, name + ".jsonl")
        run(Config(**ov), out_path=path)
        summary = G.verify_house_format(
            path, required_meta=("canary_repeats", "capacity", "seed",
                                 "entropy_level", "unique_tokens", "n_epochs"))
        assert summary["canary_repeats"] == ov["canary_repeats"]
        assert G.already_done(path), "resume check failed on a complete file"
    assert not G.already_done(os.path.join(tmp, "does_not_exist.jsonl"))

    rows = load_summaries(tmp)
    assert len(rows) == len(cells), f"readout loaded {len(rows)}/{len(cells)}"
    verdict = build_verdict(rows)
    table = render_table(verdict)
    assert verdict["sweeps"], "readout produced no sweeps"
    assert table.strip(), "readout produced an empty table"

    manifest = G.write_manifest(tmp, ARM, _cells(),
                                {"budget": BUDGET, "seeds": SEEDS})
    n_manifest = len(_cells())
    for p in os.listdir(tmp):
        os.remove(os.path.join(tmp, p))
    os.rmdir(tmp)

    print(f"SMOKE PASS: {ARM} — {len(cells)} tiny cells trained "
          f"(canary_repeats {PLANT_RATES} x n_epochs 1,2) exercising "
          f"corpus+canary planting, per-epoch eval, canary_gap probe, "
          f"jsonl _meta/_summary contract, resume skip, "
          f"MANIFEST.json ({n_manifest} planned runs -> "
          f"{os.path.basename(manifest)}) and the analyze_e1c readout "
          f"({len(verdict['sweeps'])} sweeps, {len(table.splitlines())}-line "
          f"table) in {time.time()-t0:.1f}s on CPU ({threads} torch threads)")


def main():
    ap = argparse.ArgumentParser(
        description="E1-C exposure-matched canary control (single-plant arm)")
    G.add_common_args(ap)
    add_shard_args(ap)
    args = ap.parse_args()
    validate_shard_args(args)

    if args.smoke:
        _smoke()
        sys.exit(0)

    all_cells = _cells()
    if args.pilot:
        all_cells = _pilot_cells(all_cells)
    all_cells = G.filter_cells(all_cells, args.only)
    cells = shard_cells(all_cells, args.num_shards, args.shard_id)

    if args.probe:
        for r in G.probe_tok_per_s(CAPS, Config.vocab, SEQ_LEN, BATCH_SIZE):
            print(f"PROBE {r['capacity']}: {r['n_params']:,} params, "
                  f"{r['tok_per_s']:,.0f} tok/s ({r['ms_per_step']:.1f} ms/step, "
                  f"{r['device']}); law predicted {r['law_tok_per_s']:,.0f}")
        sys.exit(0)

    if args.dry_run:
        _dry_run(cells, all_cells, args)
        sys.exit(0)

    os.makedirs(OUT, exist_ok=True)
    manifest = G.write_manifest(OUT, ARM, _cells(), {
        "budget": BUDGET, "n_ladder": N_LADDER, "plant_rates": PLANT_RATES,
        "capacities": CAPS, "entropy_levels": ENTS, "seeds": SEEDS,
        "generator": GENERATOR, "seq_len": SEQ_LEN, "batch_size": BATCH_SIZE,
    })
    print(f"[{ARM}] {len(cells)} cells -> {OUT}"
          + shard_suffix(args.num_shards, args.shard_id, len(all_cells),
                         len(cells)) + f" | manifest {manifest}", flush=True)

    failures = []
    for i, (name, ov) in enumerate(cells):
        path = os.path.join(OUT, name + ".jsonl")
        if G.already_done(path):
            print(f"[{i+1}/{len(cells)}] skip {name}", flush=True)
            continue
        t0 = time.time()
        try:
            s, _ = run(Config(**ov), out_path=path)
        except Exception as e:  # one bad cell must not drain the queue
            failures.append((name, repr(e)))
            print(f"[{i+1}/{len(cells)}] FAIL {name}: {e!r}", flush=True)
            continue
        print(f"[{i+1}/{len(cells)}] {name}: val={s['final_val_loss']:.3f} "
              f"canary_gap={s['final_canary_gap']:.3f} "
              f"({time.time()-t0:.0f}s)", flush=True)

    if failures:
        print(f"[{ARM}] {len(failures)} FAILED cells:", flush=True)
        for name, err in failures:
            print(f"    {name}: {err}", flush=True)
    print(f"[{ARM}] DONE", flush=True)


if __name__ == "__main__":
    main()
