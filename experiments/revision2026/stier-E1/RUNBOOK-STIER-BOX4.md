# BOX-4 runbook — S-E1 (real-text repetition band) + C-G3 (activation patching) — 2026-07-17

Box: `ssh -p 25814 root@connect.cqa1.seetacloud.com`, autodl-container-fbe943823b-a076e2a8,
2x RTX 4080 SUPER 32GB, torch 2.8.0+cu128 (base env + pip pyarrow), /root/autodl-tmp 100G.
Everything lives under `/root/autodl-tmp/dlr/`. Source plan:
`revision-plan-2026-0716.md` (S-E1 + C-G3); evidence notes
`revision-evidence-2026-07/{C,E1}.md`; prepped-data manifest
`box1-prepped-manifest-2026-0716.md`.

## Data provenance (all sha256-verified on arrival)

- `data/prepped_e1/` — fwe_e1_b{100,200,400}M.pt + fwe_canary_bank.pt +
  MANIFEST.json + build_prepped.py, pushed BOX-1 -> BOX-4 (BOX-1 key auth);
  hashes match BOX-1 MANIFEST (verify: sha_box4.txt).
- `data/code_src/` — github-code-clean parquets (8 files, 2.7G) pulled
  read-only from BOX-2 `dlr/data/github-code-clean/data/` (the code corpus
  family the E1 bridges already use; NOTE: task brief said "the-stack-smol"
  but BOX-2 carries github-code-clean — that IS the staged code corpus).
- `data/prepped_code/` — code_e1_b{100,200,400}M.pt + code_canary_bank.pt,
  BUILT ON BOX-4 by `build_code_shards.py` (adapted from BOX-1
  build_prepped.py; identical format contract: uint8 1-D tensor, doc sep
  b"\n\n", document-disjoint files, budget + 1M canary headroom + 2M val
  tail). MANIFEST.json alongside.
- `cg3/ckpts/` + `cg3/p1_c2/` — P1-C2 checkpoint bank (16 runs x 12 ckpts,
  manifest.jsonl) + trajectory jsonls, pulled read-only from BOX-2 pilot.
  targets.json (C1 targets, reference only) in `code/pilot_ref/`.

## Workload 1 — S-E1 (72 runs)

Runner `run_stier_e1.py`; queue split seed 50 -> GPU0, seed 51 -> GPU1
(36 runs each, identical composition). Grid:

- capacity/budget pairs: xl(d640 h8 L6, 30.06M params)/B=100M,
  xxl(d768 h8 L8, 57.31M)/B=200M, xxxl(d1280 h10 L8, ~158M NEW preset,
  d_head=128 kept, same GrokTransformer family)/B=400M. Param counts printed
  by --smoke at vocab=256 seq_len=256.
- corpus x epochs x seeds (seeds 50,51 fresh; never used by any prior E1 arm):
  fineweb n in {1,2,4,6,8,10,16} x 3 caps x 2 seeds = 42
  code    n in {2,4,10,16}      x 3 caps x 2 seeds = 24
  code    n=1 fresh-data controls x 3 caps x 2 seeds = 6   (total 72)
- protocol: run_realtext_canary conventions — AdamW lr 3e-4 wd 0.01
  betas 0.9/0.98, seq_len 256, batch 32, fp32, U = B/n, train n passes,
  fresh-val = 2M shard tail. Canaries: corpus-family bank (8x256 + matched
  fresh), planted 4x by memprobe.plant_canaries(seed=run seed) -> 4n
  exposures at epoch count n.
- DOCUMENTED DEVIATION: val_batches=16 (harness default 4) — tightens the
  fresh-val floor 4x; estimand unchanged.
- per-epoch jsonl trajectory (train/val/canary/fresh/gap + tokens_seen),
  house _meta/_summary format -> stier/results/<corpus>_<cap>_E<n>_s<seed>.jsonl
- readout `analyze_stier_e1.py`: excess vs own-sweep n=1, R_free (<0.05
  nats), decay-onset vs canary mem-onset (>0.10 nats) coincidence.

## Workload 2 — C-G3 (16 runs x 12 ckpts x 7 conditions)

Runner `run_cg3_ablate.py` (GPU1, runs BEFORE its S-E1 half; ~minutes).
Design (referee M1 evidence): mean-ablation of a component's residual-stream
contribution = replace Block.proj (attention) / Block.fc2 (MLP) output with
its per-position mean over the run's own fixed 8192-input eval set
(enumerate_dataset seed=10000+seed, identical to training-time evals), means
recomputed at each checkpoint. Conditions: none | attn | mlp (both layers) +
attn_l0/attn_l1/mlp_l0/mlp_l1 (layer-resolved secondary). All 12 checkpoints
evaluated (supersedes "final + 3 spanning deg-4 acquisition"; analyzer marks
t25/t50/t90 crossings per run). Sanity gate per run: none-condition deg_corr
must reproduce the run's logged trajectory values to <=1e-4 (asserted).
Verdict `analyze_cg3.py`: per-optimizer Δdeg4(attn), Δdeg1-3(attn),
selectivity = Δd4 - Δd1-3 (>0 = ownership, ~0 = capacity), mirrored for MLP.

## Ops

- Smoke gates: run_stier_e1.py --smoke (param counts + tiny fineweb run),
  --probe-xxxl (measured throughput -> ETA.md), run_cg3_ablate.py --smoke
  (1 run x 2 ckpts, sanity gate live).
- queue_stier.sh: nohup workers + PROGRESS.json heartbeat (progress_stier.py)
  + deadman.sh (2h log tarballs) + failsafe_watchdog.sh (10-min checks; if no
  workload process alive >90 min AND no RETRIEVED.flag -> tarball + shutdown
  -h now; stands down on RETRIEVED.flag). Laptop-side 45-min polls.
- Cell failures do NOT abort the queue (independent cells; failures_*.log).
- Disk budget: prepped_e1 0.7G + code_src 2.7G + prepped_code 0.73G +
  ckpts 0.3G + results/logs << 85G cap.
- Retrieval: stier/results + cg3/results (+ verdicts + ETA.md + PROGRESS) ->
  laptop experiments/revision2026/{stier-E1,cg3-C}/; then RETRIEVED.flag +
  shutdown -h now (user cost directive).
