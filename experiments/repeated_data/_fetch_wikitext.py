import os
for k in ['ALL_PROXY','all_proxy','HTTP_PROXY','http_proxy','HTTPS_PROXY','https_proxy','SOCKS_PROXY']:
    os.environ.pop(k, None)
import time, torch, numpy as np
from datasets import load_dataset
t=time.time()
ds = load_dataset("wikitext", "wikitext-103-raw-v1", split="train")
print("loaded rows", len(ds), "in %.1fs"%(time.time()-t), flush=True)
CAP = 64_000_000  # bytes we need (budget 50M + val + slack)
buf = bytearray()
for r in ds:
    buf.extend(r["text"].encode("utf-8"))
    if len(buf) >= CAP:
        break
arr = np.frombuffer(bytes(buf[:CAP]), dtype=np.uint8).astype(np.int64)
torch.save(torch.from_numpy(arr), "wikitext_bytes.pt")
print("saved wikitext_bytes.pt bytes=%d vocab<=256 max=%d"%(len(arr), int(arr.max())), flush=True)
