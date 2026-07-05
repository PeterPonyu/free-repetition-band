#!/usr/bin/env python3
"""Build code_bytes.pt: a byte-level source-code corpus for the E1 real-text
bridge, from Python sources already on this machine (fully offline).

Sources: CPython stdlib (/usr/lib/python3.12) + miniconda site-packages.
Exact-duplicate files removed by content hash; file order shuffled with a
fixed seed; concatenated with newline separators up to TARGET bytes.
Format matches wikitext_bytes.pt (torch uint8-valued tensor, vocab <= 256).
"""
from __future__ import annotations
import hashlib, os, random, sys
import numpy as np
import torch

TARGET = 60_000_000
ROOTS = ['/usr/lib/python3.12', '/home/zeyufu/miniconda3/lib']
OUT = '/home/zeyufu/Desktop/dl-research/experiments/repeated_data/code_bytes.pt'

files = []
for root in ROOTS:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ('test', 'tests', '__pycache__')]
        for fn in filenames:
            if fn.endswith('.py'):
                p = os.path.join(dirpath, fn)
                try:
                    sz = os.path.getsize(p)
                except OSError:
                    continue
                if 512 <= sz <= 1_000_000:
                    files.append(p)
print(f'candidate files: {len(files)}', flush=True)

rng = random.Random(20260705)
rng.shuffle(files)

seen, chunks, total = set(), [], 0
for p in files:
    try:
        b = open(p, 'rb').read()
    except OSError:
        continue
    h = hashlib.sha256(b).digest()
    if h in seen:
        continue
    seen.add(h)
    chunks.append(b + b'\n')
    total += len(b) + 1
    if total >= TARGET:
        break
print(f'kept {len(chunks)} unique files, {total} bytes', flush=True)
if total < TARGET:
    print('WARNING: corpus smaller than target', file=sys.stderr)

arr = np.frombuffer(b''.join(chunks), dtype=np.uint8).copy()
torch.save(torch.from_numpy(arr), OUT)
print(f'saved {OUT} bytes={len(arr)} max={int(arr.max())}', flush=True)
