"""E1-W — does the repetition-free band move with weight decay?

Why this arm exists
-------------------
All 541 archived E1 runs use weight_decay=0.01 (the train_repeat.Config default)
and the paper never names weight decay as an axis. Xu, Wu, Cho, Hu & Wang
(arXiv:2606.06888, June 2026, 72M-1.4B params) make strong weight decay the
central lever on repeated-epoch collapse and report that model size and data
size INTERACT under repeated data — which directly contests E1's P2 decoupling
claim. If R_free is a property of the data-repetition regime it should survive a
weight-decay sweep; if it is a property of this one regularization setting, the
free band will move with it.

Grid
----
The grid centre only — capacity=med (5.6M), entropy=med — so the sweep is a
clean one-dimensional cut through the published surface rather than a second
full grid. Everything else follows run_repeat.py conventions: B = 20M tokens
fixed, U = B/n, generator=markov, seq_len 128, batch 32, AdamW lr 3e-4
betas 0.9/0.98, val_batches 4, canaries planted 4x (the published convention;
the plant rate itself is E1-C's axis, not this one).

    weight_decay : 0, 0.01 (published), 0.1, 0.3
    n_epochs     : 1, 2, 4, 6, 8, 10, 16, 20
    seeds        : 211, 212, 213  (fresh block)
  4 x 8 x 3 = 96 runs.

The n-ladder is finer than the published {1,2,4,10,20,40} around the band edge
(6, 8 and 16 added, 40 dropped) because the readout is where R_free lands, not
the deep-repetition tail; the same ladder is used by the real-text S-E1 round,
so the two are directly comparable.

SEEDS: disjoint from the archived synthetic E1 seeds (0-14) and from the S-E1
real-text seeds (50-51); also disjoint from E1-C (201-203) and E1-F (221-223).

Readout (analyze_e1w.py): R_free, decay onset and memorization onset per weight
decay, plus the n=1 fresh baseline per weight decay so a shift of the baseline
itself cannot be mistaken for a shift of the band.

Output: experiments/revision2026/gpu2026/e1w/<name>.jsonl (+ MANIFEST.json).
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

ARM = "e1w"
BUDGET = 20_000_000
N_LADDER = [1, 2, 4, 6, 8, 10, 16, 20]
WEIGHT_DECAYS = [0.0, 0.01, 0.1, 0.3]
PUBLISHED_WD = 0.01
CAPACITY = "med"
ENTROPY = "med"
GENERATOR = "markov"
SEEDS = [211, 212, 213]

SEQ_LEN = Config.seq_len
BATCH_SIZE = Config.batch_size
N_CANARY = Config.n_canary
CANARY_REPEATS = Config.canary_repeats

OUT = os.path.join(_EXPERIMENTS_DIR, "revision2026", "gpu2026", ARM)


def _wd_tag(wd: float) -> str:
    return f"{wd:g}".replace(".", "p")


def _cells():
    """(name, overrides) for the full 96-run grid, in queue order."""
    cells = []
    for wd in WEIGHT_DECAYS:
        for n in N_LADDER:
            U = BUDGET // n
            for seed in SEEDS:
                name = f"e1w_wd{_wd_tag(wd)}_E{n}_s{seed}"
                cells.append((name, dict(
                    capacity=CAPACITY, entropy_level=ENTROPY,
                    generator=GENERATOR, unique_tokens=U, n_epochs=n,
                    total_budget=BUDGET, weight_decay=wd, seed=seed)))
    return cells


def _pilot_cells(cells):
    return [(name, ov) for name, ov in cells if ov["seed"] == SEEDS[0]]


def _eta_rows(cells):
    params = G.param_count(CAPACITY, Config.vocab, SEQ_LEN)
    fast, slow = G.est_tok_per_s(params, BATCH_SIZE * SEQ_LEN)
    hf = hs = 0.0
    for _, ov in cells:
        toks = G.tokens_per_run(ov["unique_tokens"], ov["n_epochs"], SEQ_LEN,
                                BATCH_SIZE, N_CANARY, CANARY_REPEATS)
        hf += G.run_hours(toks, fast)
        hs += G.run_hours(toks, slow)
    return params, fast, slow, hf, hs


def _dry_run(cells, all_cells, args):
    params, fast, slow, hf, hs = _eta_rows(cells)
    print(f"[{ARM}] dry-run: {len(cells)} cells planned"
          + shard_suffix(args.num_shards, args.shard_id, len(all_cells),
                         len(cells)))
    print(f"  budget B={BUDGET:,}; n-ladder={N_LADDER}; "
          f"weight_decay={WEIGHT_DECAYS} (published={PUBLISHED_WD}); "
          f"cell={CAPACITY}/{ENTROPY}; seeds={SEEDS}")
    print(f"  protocol: generator={GENERATOR} seq_len={SEQ_LEN} "
          f"batch={BATCH_SIZE} adamw lr={Config.lr} "
          f"val_batches={Config.val_batches} n_canary={N_CANARY} "
          f"canary_repeats={CANARY_REPEATS}")
    print(f"  throughput law: tok/s = {G.LAW_COEF:.3e} * params^-{G.LAW_EXP:.3f} "
          f"(fit to ETA.md anchors; ceiling {G.CEILING_STEPS_PER_S:.0f} steps/s)")
    for p, meas, pred in G.anchor_residuals():
        print(f"    anchor {p/1e6:6.1f}M params: measured {meas:>9,.0f} tok/s, "
              f"law {pred:>9,.0f} tok/s ({100*(pred-meas)/meas:+.1f}%)")
    lo, hi = G.GPU4090_SPEEDUP
    print(G.format_eta(f"{CAPACITY} ({params/1e6:.2f}M, "
                       f"{slow/1e3:.0f}-{fast/1e3:.0f}k tok/s)",
                       len(cells), hf, hs))
    print(G.format_eta("TOTAL", len(cells), hf, hs))
    print(f"  (4080-SUPER-equivalent; a 4090 is ~{lo}-{hi}x faster on this "
          f"fp32 workload. Anchors are seq_len 256, these runs are seq_len 128.)")
    for i, (name, ov) in enumerate(cells):
        print(f"  [{i+1:03d}/{len(cells)}] {name}  {ov}")


def _smoke():
    """CPU end-to-end: tiny cells through train_repeat.run + the real readout."""
    from analyze_e1w import load_summaries, build_verdict, render_table

    threads = G.limit_cpu_threads()
    t0 = time.time()
    tmp = tempfile.mkdtemp(prefix="e1w_smoke_")
    tiny = dict(unique_tokens=6144, seq_len=32, batch_size=8, vocab=64,
                capacity="small", entropy_level=ENTROPY, generator=GENERATOR,
                n_canary=4, val_batches=2, total_budget=6144, device="cpu")
    cells = []
    for wd in (WEIGHT_DECAYS[0], WEIGHT_DECAYS[-1]):
        for n in (1, 2):
            name = f"e1w_wd{_wd_tag(wd)}_E{n}_s{SEEDS[0]}"
            cells.append((name, dict(tiny, n_epochs=n, weight_decay=wd,
                                     seed=SEEDS[0])))
    for name, ov in cells:
        path = os.path.join(tmp, name + ".jsonl")
        run(Config(**ov), out_path=path)
        summary = G.verify_house_format(
            path, required_meta=("weight_decay", "capacity", "seed",
                                 "entropy_level", "unique_tokens", "n_epochs"))
        assert summary["weight_decay"] == ov["weight_decay"]
        assert G.already_done(path), "resume check failed on a complete file"
    assert not G.already_done(os.path.join(tmp, "does_not_exist.jsonl"))

    rows = load_summaries(tmp)
    assert len(rows) == len(cells), f"readout loaded {len(rows)}/{len(cells)}"
    verdict = build_verdict(rows)
    table = render_table(verdict)
    assert verdict["by_weight_decay"], "readout produced no weight-decay rows"
    assert table.strip(), "readout produced an empty table"

    manifest = G.write_manifest(tmp, ARM, _cells(),
                                {"budget": BUDGET, "seeds": SEEDS})
    n_manifest = len(_cells())
    for p in os.listdir(tmp):
        os.remove(os.path.join(tmp, p))
    os.rmdir(tmp)

    print(f"SMOKE PASS: {ARM} — {len(cells)} tiny cells trained "
          f"(weight_decay {WEIGHT_DECAYS[0]} and {WEIGHT_DECAYS[-1]} x "
          f"n_epochs 1,2) exercising the AdamW wd wiring, corpus+canary "
          f"planting, per-epoch eval, canary_gap probe, jsonl _meta/_summary "
          f"contract, resume skip, MANIFEST.json ({n_manifest} planned runs -> "
          f"{os.path.basename(manifest)}) and the analyze_e1w readout "
          f"({len(verdict['by_weight_decay'])} wd levels, "
          f"{len(table.splitlines())}-line table) in {time.time()-t0:.1f}s on "
          f"CPU ({threads} torch threads)")


def main():
    ap = argparse.ArgumentParser(
        description="E1-W weight-decay sweep on the grid-centre cell")
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
        for r in G.probe_tok_per_s([CAPACITY], Config.vocab, SEQ_LEN,
                                   BATCH_SIZE):
            print(f"PROBE {r['capacity']}: {r['n_params']:,} params, "
                  f"{r['tok_per_s']:,.0f} tok/s ({r['ms_per_step']:.1f} ms/step, "
                  f"{r['device']}); law predicted {r['law_tok_per_s']:,.0f}")
        sys.exit(0)

    if args.dry_run:
        _dry_run(cells, all_cells, args)
        sys.exit(0)

    os.makedirs(OUT, exist_ok=True)
    manifest = G.write_manifest(OUT, ARM, _cells(), {
        "budget": BUDGET, "n_ladder": N_LADDER,
        "weight_decays": WEIGHT_DECAYS, "published_weight_decay": PUBLISHED_WD,
        "capacity": CAPACITY, "entropy_level": ENTROPY, "seeds": SEEDS,
        "generator": GENERATOR, "seq_len": SEQ_LEN, "batch_size": BATCH_SIZE,
        "canary_repeats": CANARY_REPEATS,
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
