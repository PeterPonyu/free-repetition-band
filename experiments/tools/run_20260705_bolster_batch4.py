#!/usr/bin/env python3
"""Batch 4 of the bolstering runs (2026-07-05 evening).

E1:
  B8: small/{low,med} at n=12,16 x s0-9 — completes the fine grid in the two
      boundary cells (incl. the one dissociating cell, small/low) so the
      decay-vs-memorization onset gap there is measured, not inferred.
  B9: fine grid in two MORE cells (small/high, large/low) at n in {6,8,12,16}
      x s0-2 — P4 shape universality beyond the two probed corners.
[The cells of another study in this batch, A9 to A11, are omitted from this public copy.]
All cells resume-aware; distinct filenames never clobber existing logs.
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

def finegrid_cmd(cap, ent, E, U, s):
    name = f"{cap}_{ent}_U{U/1e6:g}M_E{E}_s{s}".replace('.', 'p')
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
        f"cfg = Config(capacity='{cap}', entropy_level='{ent}', generator='markov',\n"
        f"             unique_tokens={U}, n_epochs={E}, total_budget=20_000_000, seed={s})\n"
        "run(cfg, out_path=str(out))\n")
    return (name, [PY, '-c', code])


def cell_cmds():
    cmds = []
    # B8: boundary-cell fine-grid completion via the seed-audit runner (small cap)
    for ent in ('low', 'med'):
        for U in (1_666_667, 1_250_000):  # E=12, E=16
            for s in range(10):
                cmds.append((f'B8 small_{ent} U{U} s{s}',
                             [PY, 'repeated_data/run_e1_seed_audit_cell.py',
                              '--entropy', ent, '--unique-tokens', str(U),
                              '--seed', str(s)]))
    # B9: two more fine-grid cells
    for cap, ent in (('small', 'high'), ('large', 'low')):
        for E, U in [(6, 3_333_333), (8, 2_500_000), (12, 1_666_667), (16, 1_250_000)]:
            for s in range(3):
                d, args = finegrid_cmd(cap, ent, E, U, s)
                cmds.append((f'B9 {d}', args))
    # A9 to A11: [cells of another study are omitted from this public copy.]
    return cmds


def run_cell(item):
    desc, args = item
    t0 = time.time()
    r = subprocess.run(args, cwd=str(EXP), capture_output=True, text=True)
    dt = (time.time() - t0) / 60
    tail = (r.stdout or '').strip().splitlines()[-1:] or ['']
    print(f"[par4] {desc}: rc={r.returncode} ({dt:.1f} min) {tail[0][:120]}", flush=True)
    if r.returncode != 0:
        print((r.stderr or '')[-800:], flush=True)
    return (desc, r.returncode)


if __name__ == '__main__':
    cmds = cell_cmds()
    print(f"[par4] {len(cmds)} cells, {N_WORKERS} workers", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=N_WORKERS) as ex:
        results = list(ex.map(run_cell, cmds))
    bad = [d for d, rc in results if rc != 0]
    print(f"[par4] TOTAL {(time.time()-t0)/60:.1f} min; failures: {len(bad)} {bad}", flush=True)
