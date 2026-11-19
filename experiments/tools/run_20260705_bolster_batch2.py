#!/usr/bin/env python3
"""Batch 2 of the bolstering runs (2026-07-05). See batch 1:
run_20260704_bolster_parallel.py. All cells independent + resume-aware.

[The cells of another study in this batch are omitted from this public copy.]
E1: small/{low,med} U=1M (n=20) s5-14 (dissociation cell + corner edge);
realtext med_b50M s2-4 (bridge 2->5 seeds); large/high fine grid
E in {6,8,12,16} x s0-2 (decay-shape universality).
"""
from __future__ import annotations
import subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / 'experiments'
PY = sys.executable
N_WORKERS = 6
FINE_OUT = EXP / 'results' / 'repeated_data_finegrid'

def cell_cmds():
    cmds = []
    # [Cells of another study are omitted from this public copy.]
    # E1 upper-edge / dissociation cells: U=1M (n=20), s5-14
    for ent in ('low', 'med'):
        for s in range(5, 15):
            cmds.append((f'B1 small_{ent} U1M s{s}',
                         [PY, 'repeated_data/run_e1_seed_audit_cell.py',
                          '--entropy', ent, '--unique-tokens', '1000000',
                          '--seed', str(s)]))
    # E1 realtext bridge s2-4 (runner is idempotent per seed-file? it writes
    # <cap>_b50M_s<seed>.json; skip if exists)
    for s in (2, 3, 4):
        out = EXP / 'results' / 'repeated_data_realtext' / f'med_b50M_s{s}.json'
        if out.exists():
            continue
        cmds.append((f'B2 realtext med b50M s{s}',
                     [PY, 'repeated_data/run_20260619_e1_realtext.py',
                      '--budget', '50000000', '--capacity', 'med',
                      '--seeds', str(s)]))
    # E1 large/high fine grid
    for E, U in [(6, 3_333_333), (8, 2_500_000), (12, 1_666_667), (16, 1_250_000)]:
        for s in range(3):
            name = f"large_high_U{U/1e6:g}M_E{E}_s{s}".replace('.', 'p')
            out = FINE_OUT / f"{name}.jsonl"
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
                f"cfg = Config(capacity='large', entropy_level='high', generator='markov',\n"
                f"             unique_tokens={U}, n_epochs={E}, total_budget=20_000_000, seed={s})\n"
                "run(cfg, out_path=str(out))\n")
            cmds.append((f'B3 {name}', [PY, '-c', code]))
    return cmds


def run_cell(item):
    desc, args = item
    t0 = time.time()
    r = subprocess.run(args, cwd=str(EXP), capture_output=True, text=True)
    dt = (time.time() - t0) / 60
    tail = (r.stdout or '').strip().splitlines()[-1:] or ['']
    print(f"[par2] {desc}: rc={r.returncode} ({dt:.1f} min) {tail[0][:120]}", flush=True)
    if r.returncode != 0:
        print((r.stderr or '')[-800:], flush=True)
    return (desc, r.returncode)


if __name__ == '__main__':
    cmds = cell_cmds()
    print(f"[par2] {len(cmds)} cells, {N_WORKERS} workers", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=N_WORKERS) as ex:
        results = list(ex.map(run_cell, cmds))
    bad = [d for d, rc in results if rc != 0]
    print(f"[par2] TOTAL {(time.time()-t0)/60:.1f} min; failures: {len(bad)} {bad}", flush=True)
