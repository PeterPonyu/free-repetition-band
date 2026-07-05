#!/usr/bin/env python3
"""Batch 5 (red-team-driven, E1 arms; 2026-07-05 late).

L1: lr sensitivity on med/med (red-team M2 — the mechanism's own knob):
    lr in {1e-4, 1e-3} (grid default is 3e-4) x n in {2,4,6,8,10} x s0-2.
S1: WikiText corpus-draw replication (M1): disjoint shards 0-2, seed 0 each.
S2: code-v2 near-dedup corpus (K2): disjoint shards 0-2, seed 0 each —
    adjudicates whether R_free=2 was a near-duplication artifact.
"""
from __future__ import annotations
import subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path('/home/zeyufu/Desktop/dl-research')
EXP = ROOT / 'experiments'
PY = sys.executable
N_WORKERS = 6
LR_OUT = EXP / 'results' / 'repeated_data_lrsweep'


def lr_cell(lr, E, U, s):
    tag = f"lr{lr:g}".replace('-', 'm').replace('.', 'p')
    name = f"med_med_{tag}_U{U/1e6:g}M_E{E}_s{s}".replace('.', 'p')
    out = LR_OUT / f"{name}.jsonl"
    code = (
        "import json, sys; from pathlib import Path\n"
        "sys.path.insert(0, 'repeated_data')\n"
        f"out = Path({str(out)!r})\n"
        "if out.exists():\n"
        "    last = ''\n"
        "    for line in out.open():\n"
        "        if line.strip(): last = line\n"
        "    try:\n"
        "        if '_summary' in json.loads(last):\n"
        f"            print('skip {name} (complete)'); raise SystemExit(0)\n"
        "    except SystemExit: raise\n"
        "    except Exception: pass\n"
        "    out.unlink()\n"
        "out.parent.mkdir(parents=True, exist_ok=True)\n"
        "from train_repeat import Config, run\n"
        f"cfg = Config(capacity='med', entropy_level='med', generator='markov',\n"
        f"             unique_tokens={U}, n_epochs={E}, total_budget=20_000_000,\n"
        f"             lr={lr}, seed={s})\n"
        "run(cfg, out_path=str(out))\n")
    return (name, [PY, '-c', code])


def cell_cmds():
    cmds = []
    for lr in (1e-4, 1e-3):
        for E, U in [(2, 10_000_000), (4, 5_000_000), (6, 3_333_333),
                     (8, 2_500_000), (10, 2_000_000)]:
            for s in range(3):
                d, args = lr_cell(lr, E, U, s)
                cmds.append((f'L1 {d}', args))
    # lr-matched fresh baselines (n=1) so excess is computed within-lr
    for lr in (1e-4, 1e-3):
        for s in range(3):
            d, args = lr_cell(lr, 1, 20_000_000, s)
            cmds.append((f'L1 {d}', args))
    for k in range(3):
        cmds.append((f'S1 wiki_shard{k}',
                     [PY, 'repeated_data/run_realtext_shard.py',
                      '--bytes-file', f'repeated_data/wiki_shard{k}.pt',
                      '--tag', f'wiki_shard{k}', '--seed', '0']))
        cmds.append((f'S2 code_v2_shard{k}',
                     [PY, 'repeated_data/run_realtext_shard.py',
                      '--bytes-file', f'repeated_data/code_v2_shard{k}.pt',
                      '--tag', f'code_v2_shard{k}', '--seed', '0']))
    return cmds


def run_cell(item):
    desc, args = item
    t0 = time.time()
    r = subprocess.run(args, cwd=str(EXP), capture_output=True, text=True)
    dt = (time.time() - t0) / 60
    tail = (r.stdout or '').strip().splitlines()[-1:] or ['']
    print(f"[par5] {desc}: rc={r.returncode} ({dt:.1f} min) {tail[0][:120]}", flush=True)
    if r.returncode != 0:
        print((r.stderr or '')[-800:], flush=True)
    return (desc, r.returncode)


if __name__ == '__main__':
    cmds = cell_cmds()
    print(f"[par5] {len(cmds)} cells, {N_WORKERS} workers", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=N_WORKERS) as ex:
        results = list(ex.map(run_cell, cmds))
    bad = [d for d, rc in results if rc != 0]
    print(f"[par5] TOTAL {(time.time()-t0)/60:.1f} min; failures: {len(bad)} {bad}", flush=True)
