#!/usr/bin/env python3
"""Consolidated analysis of the 2026-07-04/05 bolstering batches (1-3).

Prints the numbers taken from these batches:
  [The sections for another study are omitted from this public copy.]
  [E1-ONSET]  small/{low,med} excess medians at n in {4,6,8,10,20}
  [E1-SHAPE]  med/med + large/high fine-grid excess vs n, log-log slope
  [E1-REAL]   WikiText vs code-bytes bridge: R_free + per-n excess (all seeds)
CPU only; safe to run while batches are in flight (prints current n per cell).
"""
from __future__ import annotations
import glob, json, math, statistics as st
from pathlib import Path

RES = Path(__file__).resolve().parents[2] / 'experiments' / 'results'


def jlast(f):
    last = None
    for line in open(f):
        if line.strip():
            last = json.loads(line)
    return last


def jrows(f):
    return [json.loads(l) for l in open(f) if l.strip()]


# ---------------- E1 onsets + shape ----------------
def summ(f):
    return jlast(f)['_summary']


def cell_excess(cap, ent, E, U_tag):
    """median excess over available seeds; searches main+audit+finegrid dirs"""
    pats = [RES / 'repeated_data' / f'{cap}_{ent}_U{U_tag}_E{E}_s*.jsonl',
            RES / 'repeated_data_ultragoal_seed_audit' / f'{cap}_{ent}_U{U_tag}_E{E}_s*.jsonl',
            RES / 'repeated_data_finegrid' / f'{cap}_{ent}_U{U_tag}_E{E}_s*.jsonl']
    fs = sorted(set(sum([glob.glob(str(p)) for p in pats], [])))
    fresh = [summ(f)['final_val_loss'] for f in
             glob.glob(str(RES / 'repeated_data' / f'{cap}_{ent}_U20M_E1_s*.jsonl'))]
    if not fs or not fresh:
        return None
    fm = st.median(fresh)
    ex = [summ(f)['final_val_loss'] - fm for f in fs]
    cg = [summ(f)['final_canary_gap'] for f in fs]
    return dict(n=len(ex), med=st.median(ex), lo=min(ex), hi=max(ex),
                canary_med=st.median(cg))


print('=' * 30, 'E1-ONSET (small cells)', '=' * 30)
for ent in ('low', 'med'):
    for E, U_tag in ((4, '5M'), (6, '3p33333M'), (8, '2p5M'), (10, '2M'), (20, '1M')):
        r = cell_excess('small', ent, E, U_tag)
        if r:
            print(f"small/{ent} n={E:2d}: seeds={r['n']:2d} excess med {r['med']:+.4f} "
                  f"[{r['lo']:+.4f},{r['hi']:+.4f}] canary {r['canary_med']:+.4f}")

print('=' * 30, 'E1-SHAPE (fine grid)', '=' * 30)
for cap, ent in (('med', 'med'), ('large', 'high')):
    pts = []
    for E, U_tag in ((2, '10M'), (4, '5M'), (6, '3p33333M'), (8, '2p5M'),
                     (10, '2M'), (12, '1p66667M'), (16, '1p25M'), (20, '1M'), (40, '0p5M')):
        r = cell_excess(cap, ent, E, U_tag)
        if r:
            print(f"{cap}/{ent} n={E:2d}: seeds={r['n']:2d} excess med {r['med']:+.4f} "
                  f"[{r['lo']:+.4f},{r['hi']:+.4f}] canary {r['canary_med']:+.4f}")
            if r['med'] > 0.05:
                pts.append((E, r['med']))
    if len(pts) >= 3:
        xs = [math.log(e) for e, _ in pts]
        ys = [math.log(v) for _, v in pts]
        n = len(xs)
        b = (n * sum(x * y for x, y in zip(xs, ys)) - sum(xs) * sum(ys)) / \
            (n * sum(x * x for x in xs) - sum(xs) ** 2)
        print(f'  {cap}/{ent} post-threshold log-log slope: {b:.2f} '
              f'(points n={[e for e,_ in pts]})')

# ---------------- E1 real-text ----------------
print('=' * 30, 'E1-REAL (byte-level bridges, budget 50M, med cap)', '=' * 30)
for label, d in (('WikiText', RES / 'repeated_data_realtext'),
                 ('code', RES / 'repeated_data_realtext_code')):
    fs = sorted(glob.glob(str(d / 'med_b50M_s*.json')))
    if not fs:
        continue
    rfree, rowsets = [], []
    for f in fs:
        v = json.load(open(f))
        rfree.append(v['R_free'])
        rowsets.append({k: r['excess'] for k, r in v['rows'].items()})
    ns = sorted({int(k) for rs in rowsets for k in rs}, key=int)
    print(f'{label}: seeds={len(fs)} R_free={rfree}')
    for n in ns:
        vals = [rs[str(n)] for rs in rowsets if str(n) in rs]
        print(f'   n={n:2d}: excess med {st.median(vals):+.4f} '
              f'[{min(vals):+.4f},{max(vals):+.4f}] (n={len(vals)})')
