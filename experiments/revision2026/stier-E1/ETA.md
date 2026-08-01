# BOX-4 measured ETA (2026-07-17, pre-launch)

Measured fp32 training throughput (200-step probe, batch 32 x seq 256, AdamW,
RTX 4080 SUPER, harness-convention precision):

| capacity | params | tok/s | h per run (budget) | runs | GPU-h |
|---|---|---|---|---|---|
| xl   | 30.0M  | 124,089 | 0.22 (100M) | 24 | 5.4 |
| xxl  | 57.2M  |  67,920 | 0.82 (200M) | 24 | 19.6 |
| xxxl | 158.3M |  27,223 | 4.08 (400M) | 24 | 98.0 |

S-E1 total: 72 runs = ~123 GPU-h; split seed-50 -> GPU0 / seed-51 -> GPU1
(36 runs each, identical composition) => wall-clock ~61-64 h (~2.6 days),
finish est. 2026-07-20 ~06:00 box time (+ per-run eval/load overhead ~2-3%).
Order per GPU: xl (first signals ~3 h in) -> xxl -> xxxl.

C-G3: 16 runs x 12 ckpts x 7 conditions, runs FIRST on GPU1, ~10-20 min
total; verdict json immediately after.

Smoke gates (all PASS): C-G3 sanity dev=0 vs logged trajectories; S-E1
fineweb tiny run (per-epoch jsonl OK); code-corpus tiny run end-to-end OK;
param counts xl/xxl/xxxl = 29,999,360 / 57,239,040 / 158,312,960.
Code shards built + manifested on-box (document-disjoint, sha256 logged).
Disk high-water ~4.5G << 85G cap.
