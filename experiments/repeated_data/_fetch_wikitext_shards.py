"""Build three DISJOINT WikiText-103 byte shards for corpus-level replication
(red-team M1: the original five "seeds" reran one fixed corpus draw).

Each shard file is self-contained: 52M train bytes + 2M val tail = 54M,
cut sequentially from the wikitext-103-raw train stream (shard k covers
bytes [k*54M, (k+1)*54M) of the stream; shard 0 therefore overlaps the
original wikitext_bytes.pt draw and acts as the continuity anchor).
"""
import os
for k in ['ALL_PROXY', 'all_proxy', 'HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY',
          'https_proxy', 'SOCKS_PROXY']:
    os.environ.pop(k, None)
import time
import numpy as np
import torch
from datasets import load_dataset

SHARD = 54_000_000
N_SHARDS = 3
CAP = SHARD * N_SHARDS

t = time.time()
ds = load_dataset("wikitext", "wikitext-103-raw-v1", split="train")
print("loaded rows", len(ds), "in %.1fs" % (time.time() - t), flush=True)
buf = bytearray()
for r in ds:
    buf.extend(r["text"].encode("utf-8"))
    if len(buf) >= CAP:
        break
if len(buf) < CAP:
    raise SystemExit(f"stream exhausted at {len(buf)} < {CAP} bytes")
for k in range(N_SHARDS):
    arr = np.frombuffer(bytes(buf[k * SHARD:(k + 1) * SHARD]),
                        dtype=np.uint8).astype(np.int64)
    out = f"wiki_shard{k}.pt"
    torch.save(torch.from_numpy(arr), out)
    print(f"saved {out} bytes={len(arr)} max={int(arr.max())}", flush=True)
