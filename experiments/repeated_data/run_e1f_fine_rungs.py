"""E1-F — fine rungs and a fresh baseline at the top of the capacity span.

Why this arm exists
-------------------
The xl (30.0M) and xxl (57.2M) cells that stretch E1's capacity span to ~23x
were run by run_20260708_capacity_xl.py on n in {2, 4, 10, 20} only: 2.5x
spacing, 3 seeds at xl and 2 at xxl, and no n=1 run at all. The band claim
(R_free = 4, decay onset = 10) therefore rests, at the top of the span, on a
grid whose rungs are further apart than the effect being measured and on a
fresh-data reference that had to come from outside the sweep. The "the band is
a measurement, not a grid artifact" argument does not cover those cells.

This arm reruns the top of the span on a ladder that adds the missing rungs:

    n_epochs : 1, 2, 4, 6, 8, 10, 20
               ^ new     ^ new
    capacity : xl  (d640 h8 L6) x entropy {low, med, high}
               xxl (d768 h8 L8) x entropy {med}
    seeds    : 221, 222, 223  (fresh block; xxl gets 3 rather than the
               published 2)
  xl 3 x 7 x 3 = 63, xxl 1 x 7 x 3 = 21, total 84 runs.

The full ladder is rerun rather than only {1, 6, 8} so that excess is computed
against an n=1 run from the SAME seed block and the same sweep, which is the
published convention (analyze_repeat.py, analyze_stier_e1.py) and the only way
the fine and coarse grids can be compared on identical data. The rungs
{2, 4, 10, 20} at fresh seeds double as an independent replication of the
published capxl cells. Presets and budget are exactly
run_20260708_capacity_xl.py's: B = 20M tokens, U = B/n, generator=markov,
seq_len 128, batch 32, AdamW lr 3e-4 wd 0.01, val_batches 4, canaries planted
4x. The added cost over the minimal {1, 6, 8} version is about 2 GPU-h.

SEEDS: the capxl arm used 0-2 (xl) and 0-1 (xxl); the wider synthetic E1 family
has used 0-14 and the real-text S-E1 round 50-51. 221-223 is disjoint from all
of them, and from E1-C (201-203) and E1-W (211-213).

Readout (analyze_e1f.py): R_free / decay onset / memorization onset per sweep
and pooled, computed twice on the SAME runs — once on the full fine ladder and
once restricted to the published coarse rungs {1, 2, 4, 10, 20} — so any
disagreement is attributable to grid spacing alone.

Output: experiments/revision2026/gpu2026/e1f/<name>.jsonl (+ MANIFEST.json).
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
from model import CAPACITY_PRESETS  # noqa: E402
from runner_utils import (  # noqa: E402
    add_shard_args, shard_cells, shard_suffix, validate_shard_args,
)

ARM = "e1f"
BUDGET = 20_000_000
N_LADDER = [1, 2, 4, 6, 8, 10, 20]
PUBLISHED_RUNGS = [2, 4, 10, 20]      # run_20260708_capacity_xl.py's ladder
NEW_RUNGS = [1, 6, 8]
CAP_ENTROPY = [("xl", ["low", "med", "high"]), ("xxl", ["med"])]
GENERATOR = "markov"
SEEDS = [221, 222, 223]

SEQ_LEN = Config.seq_len
BATCH_SIZE = Config.batch_size
N_CANARY = Config.n_canary
CANARY_REPEATS = Config.canary_repeats

OUT = os.path.join(_EXPERIMENTS_DIR, "revision2026", "gpu2026", ARM)


def _tag_u(U: int) -> str:
    return f"{U/1e6:g}M".replace(".", "p")


def _cells():
    """(name, overrides) for the full 84-run grid, in queue order."""
    cells = []
    for cap, ents in CAP_ENTROPY:
        for ent in ents:
            for n in N_LADDER:
                U = BUDGET // n
                for seed in SEEDS:
                    name = (f"e1f_{cap}_{ent}_U{_tag_u(U)}_E{n}_s{seed}")
                    cells.append((name, dict(
                        capacity=cap, entropy_level=ent, generator=GENERATOR,
                        unique_tokens=U, n_epochs=n, total_budget=BUDGET,
                        seed=seed)))
    return cells


def _pilot_cells(cells):
    """Smallest complete sub-grid: the xl/med sweep at the first seed."""
    return [(name, ov) for name, ov in cells
            if ov["capacity"] == "xl" and ov["entropy_level"] == "med"
            and ov["seed"] == SEEDS[0]]


def _eta_rows(cells):
    caps = sorted({ov["capacity"] for _, ov in cells})
    params = {cap: G.param_count(cap, Config.vocab, SEQ_LEN) for cap in caps}
    rows = {}
    for _, ov in cells:
        cap = ov["capacity"]
        toks = G.tokens_per_run(ov["unique_tokens"], ov["n_epochs"], SEQ_LEN,
                                BATCH_SIZE, N_CANARY, CANARY_REPEATS)
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
    print(f"  budget B={BUDGET:,}; n-ladder={N_LADDER} "
          f"(published rungs {PUBLISHED_RUNGS}, new {NEW_RUNGS}); "
          f"seeds={SEEDS}")
    for cap, ents in CAP_ENTROPY:
        print(f"  {cap:<4} preset={CAPACITY_PRESETS[cap]} "
              f"n_params={params.get(cap, 0):,} "
              f"({params.get(cap, 0)/1e6:.2f}M) entropy={ents}")
    print(f"  protocol: generator={GENERATOR} seq_len={SEQ_LEN} "
          f"batch={BATCH_SIZE} adamw lr={Config.lr} wd={Config.weight_decay} "
          f"val_batches={Config.val_batches} n_canary={N_CANARY} "
          f"canary_repeats={CANARY_REPEATS}")
    print(f"  throughput law: tok/s = {G.LAW_COEF:.3e} * params^-{G.LAW_EXP:.3f} "
          f"(fit to ETA.md anchors; ceiling {G.CEILING_STEPS_PER_S:.0f} steps/s)")
    for p, meas, pred in G.anchor_residuals():
        print(f"    anchor {p/1e6:6.1f}M params: measured {meas:>9,.0f} tok/s, "
              f"law {pred:>9,.0f} tok/s ({100*(pred-meas)/meas:+.1f}%)")
    tot_f = tot_s = 0.0
    for cap, _ in CAP_ENTROPY:
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
          f"fp32 workload. The xl anchor in ETA.md is this exact preset, "
          f"measured at seq_len 256; these runs are seq_len 128.)")
    for i, (name, ov) in enumerate(cells):
        print(f"  [{i+1:03d}/{len(cells)}] {name}  {ov}")


def _smoke():
    """CPU end-to-end: tiny cells through train_repeat.run + the real readout,
    plus one real forward/backward/step at the xl and xxl presets so the
    expensive capacity path is covered without paying for a full run."""
    from analyze_e1f import load_summaries, build_verdict, render_table

    threads = G.limit_cpu_threads()
    t0 = time.time()
    caps = []
    for cap, _ in CAP_ENTROPY:
        n_params, loss = G.one_step_check(cap, Config.vocab, SEQ_LEN, batch=2)
        assert n_params > 0 and loss == loss, f"{cap}: bad step"
        caps.append((cap, n_params, loss))

    tmp = tempfile.mkdtemp(prefix="e1f_smoke_")
    tiny = dict(unique_tokens=6144, seq_len=32, batch_size=8, vocab=64,
                capacity="small", entropy_level="med", generator=GENERATOR,
                n_canary=4, val_batches=2, total_budget=6144, device="cpu")
    cells = []
    for n in (1, 2, 4):
        name = f"e1f_small_med_U6144_E{n}_s{SEEDS[0]}"
        cells.append((name, dict(tiny, n_epochs=n, seed=SEEDS[0])))
    for name, ov in cells:
        path = os.path.join(tmp, name + ".jsonl")
        run(Config(**ov), out_path=path)
        G.verify_house_format(
            path, required_meta=("capacity", "seed", "entropy_level",
                                 "unique_tokens", "n_epochs", "canary_repeats"))
        assert G.already_done(path), "resume check failed on a complete file"
    assert not G.already_done(os.path.join(tmp, "does_not_exist.jsonl"))

    rows = load_summaries(tmp)
    assert len(rows) == len(cells), f"readout loaded {len(rows)}/{len(cells)}"
    verdict = build_verdict(rows)
    table = render_table(verdict)
    assert verdict["cells"], "readout produced no cells"
    assert table.strip(), "readout produced an empty table"

    manifest = G.write_manifest(tmp, ARM, _cells(),
                                {"budget": BUDGET, "seeds": SEEDS})
    n_manifest = len(_cells())
    for p in os.listdir(tmp):
        os.remove(os.path.join(tmp, p))
    os.rmdir(tmp)

    caps_str = ", ".join(f"{c}={n/1e6:.2f}M params (loss {l:.3f})"
                         for c, n, l in caps)
    print(f"SMOKE PASS: {ARM} — real train step at the production presets "
          f"[{caps_str}] plus {len(cells)} tiny cells trained (n_epochs 1,2,4) "
          f"exercising corpus+canary planting, per-epoch eval, canary_gap "
          f"probe, jsonl _meta/_summary contract, resume skip, MANIFEST.json "
          f"({n_manifest} planned runs -> {os.path.basename(manifest)}) and "
          f"the analyze_e1f fine-vs-coarse readout ({len(verdict['cells'])} "
          f"cells, {len(table.splitlines())}-line table) in "
          f"{time.time()-t0:.1f}s on CPU ({threads} torch threads)")


def main():
    ap = argparse.ArgumentParser(
        description="E1-F fine rungs at the top of the capacity span")
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
        for r in G.probe_tok_per_s([c for c, _ in CAP_ENTROPY], Config.vocab,
                                   SEQ_LEN, BATCH_SIZE):
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
        "published_rungs": PUBLISHED_RUNGS, "new_rungs": NEW_RUNGS,
        "cap_entropy": {cap: ents for cap, ents in CAP_ENTROPY},
        "seeds": SEEDS, "generator": GENERATOR, "seq_len": SEQ_LEN,
        "batch_size": BATCH_SIZE, "canary_repeats": CANARY_REPEATS,
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
