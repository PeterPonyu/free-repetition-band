#!/usr/bin/env python3
"""Code corpus v2 (red-team K2/M1): exact dedup + MinHash NEAR-dedup, then
three DISJOINT shards for corpus-level replication.

Near-dedup: 32-byte shingles, 64 MinHash permutations, greedy clustering by
banded LSH; a file is dropped if its estimated Jaccard similarity to an
already-kept file is >= 0.8. Deterministic (fixed hash seeds, fixed shuffle).

Outputs (repeated_data/): code_v2_shard{0,1,2}.pt (54M each: 52M train + 2M
val tail, disjoint file sets) + stats printed (kept/dropped counts, gzip
bits/byte per shard).
"""
from __future__ import annotations
import gzip, hashlib, os, random
import numpy as np
import torch

ROOTS = ['/usr/lib/python3.12', '/home/zeyufu/miniconda3/lib']
OUTDIR = '/home/zeyufu/Desktop/dl-research/experiments/repeated_data'
SHARD = 54_000_000
N_SHARDS = 3
K_SHINGLE = 32
N_PERM = 64
BANDS = 16          # 16 bands x 4 rows: catches J>=~0.7-0.8 reliably
JACCARD_DROP = 0.8

MASK = (1 << 61) - 1
rnd = random.Random(20260705)
PERMS = [(rnd.randrange(1, MASK), rnd.randrange(0, MASK)) for _ in range(N_PERM)]


def shingle_hashes(b: bytes):
    hs = set()
    step = max(1, (len(b) - K_SHINGLE) // 512)  # sample <=512 shingles/file
    for i in range(0, max(1, len(b) - K_SHINGLE), step):
        hs.add(int.from_bytes(hashlib.blake2b(b[i:i + K_SHINGLE],
                                              digest_size=8).digest(), 'big'))
    return hs


def minhash(hs):
    sig = []
    for a, c in PERMS:
        sig.append(min(((a * h + c) & MASK) for h in hs) if hs else 0)
    return sig


def main():
    files = []
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in ('test', 'tests', '__pycache__')]
            for fn in filenames:
                if fn.endswith('.py'):
                    p = os.path.join(dirpath, fn)
                    try:
                        sz = os.path.getsize(p)
                    except OSError:
                        continue
                    if 512 <= sz <= 1_000_000:
                        files.append(p)
    print(f'candidates: {len(files)}', flush=True)
    rng = random.Random(20260705)
    rng.shuffle(files)

    seen_exact = set()
    lsh_buckets: dict[tuple, list[int]] = {}
    kept_sigs: list[list[int]] = []
    kept_bytes: list[bytes] = []
    n_exact = n_near = 0
    rows_per_band = N_PERM // BANDS
    target_total = SHARD * N_SHARDS + 2_000_000

    for p in files:
        if sum(len(b) + 1 for b in kept_bytes) >= target_total:
            break
        try:
            b = open(p, 'rb').read()
        except OSError:
            continue
        h = hashlib.sha256(b).digest()
        if h in seen_exact:
            n_exact += 1
            continue
        seen_exact.add(h)
        hs = shingle_hashes(b)
        sig = minhash(hs)
        cand = set()
        keys = []
        for bi in range(BANDS):
            key = (bi, tuple(sig[bi * rows_per_band:(bi + 1) * rows_per_band]))
            keys.append(key)
            cand.update(lsh_buckets.get(key, ()))
        is_near = False
        for ci in cand:
            est = sum(a == b2 for a, b2 in zip(sig, kept_sigs[ci])) / N_PERM
            if est >= JACCARD_DROP:
                is_near = True
                break
        if is_near:
            n_near += 1
            continue
        idx = len(kept_sigs)
        kept_sigs.append(sig)
        kept_bytes.append(b)
        for key in keys:
            lsh_buckets.setdefault(key, []).append(idx)

    total = sum(len(b) + 1 for b in kept_bytes)
    print(f'kept {len(kept_bytes)} files ({total} bytes); '
          f'exact-dropped {n_exact}, NEAR-dropped {n_near}', flush=True)
    if total < SHARD * N_SHARDS:
        print(f'WARNING: only {total} bytes; shards will be truncated')

    stream = b''.join(b + b'\n' for b in kept_bytes)
    for k in range(N_SHARDS):
        chunk = stream[k * SHARD:(k + 1) * SHARD]
        if len(chunk) < SHARD:
            print(f'shard{k}: only {len(chunk)} bytes, skipping')
            continue
        arr = np.frombuffer(chunk, dtype=np.uint8).copy().astype(np.int64)
        out = os.path.join(OUTDIR, f'code_v2_shard{k}.pt')
        torch.save(torch.from_numpy(arr), out)
        comp = len(gzip.compress(chunk[:20_000_000], 9))
        print(f'saved {out} bytes={len(arr)} gzip9={comp/20_000_000*8:.3f} bits/byte',
              flush=True)


if __name__ == '__main__':
    main()
