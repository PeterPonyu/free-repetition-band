"""Shared plumbing for the 2026 GPU-round E1 arms (E1-C, E1-W, E1-F).

All three runners are thin grid wrappers over the UNCHANGED train_repeat.run
harness: each arm varies only fields that already exist on train_repeat.Config
(canary_repeats, weight_decay, capacity, n_epochs, seed), so the trainer, the
canary machinery (memprobe) and the jsonl contract stay the published ones.
What is genuinely new — and therefore lives here rather than being triplicated —
is the GPU-time estimator, the run manifest, and the CPU smoke helpers that gate
the GPU launch.

Throughput model (used by --dry-run)
------------------------------------
Anchors are the MEASURED fp32 throughputs in
experiments/revision2026/stier-E1/ETA.md (RTX 4080 SUPER, batch 32 x seq_len
256, AdamW): 30.0M -> 124,089 tok/s, 57.2M -> 67,920 tok/s, 158.3M -> 27,223
tok/s. A log-log least-squares fit of those three points gives

    tok/s ~= LAW_COEF * n_params ** (-LAW_EXP)      (LAW_EXP ~= 0.92)

reproducing all three anchors to ~1%. That law is compute-bound, so it
EXTRAPOLATES OPTIMISTICALLY below the smallest anchor: the {small, med, large}
presets of this study (2.5M-9.9M params) are kernel-launch bound rather than
FLOP bound at batch 32. Every estimate is therefore quoted as a range whose
slow end applies a launch-bound ceiling of CEILING_STEPS_PER_S steps/s. That
ceiling is an ASSUMPTION, not a measurement; `--probe` replaces both numbers
with a measured tok/s as soon as a GPU exists.

Two further caveats, both folded into the quoted range: the anchors are at
seq_len 256 while these arms train at seq_len 128 (step time scales sub-linearly
in sequence length, so applying the law unscaled is mildly optimistic), and the
anchors exclude per-run corpus generation and eval overhead (~2-3% on the S-E1
round).

All estimates are 4080-SUPER-equivalent GPU-hours. An RTX 4090 is roughly
1.3-1.6x faster on this fp32 workload, so divide by that factor for 4090
wall-clock.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone

# (n_params, tok/s) measured on RTX 4080 SUPER, fp32, batch 32 x seq_len 256.
ANCHORS = [
    (29_999_360, 124_089.0),
    (57_239_040, 67_920.0),
    (158_312_960, 27_223.0),
]
CEILING_STEPS_PER_S = 120.0     # launch-bound ASSUMPTION for the small presets
GPU4090_SPEEDUP = (1.3, 1.6)    # 4080 SUPER -> 4090, this fp32 workload


def _fit_power_law(anchors) -> tuple[float, float]:
    """Least-squares fit of log(tok/s) = log(coef) - exp * log(params)."""
    xs = [math.log(p) for p, _ in anchors]
    ys = [math.log(t) for _, t in anchors]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sxy / sxx
    return math.exp(my - slope * mx), -slope


LAW_COEF, LAW_EXP = _fit_power_law(ANCHORS)


def law_tok_per_s(n_params: int) -> float:
    return LAW_COEF * float(n_params) ** (-LAW_EXP)


def anchor_residuals() -> list[tuple[int, float, float]]:
    """(params, measured, predicted) for each anchor — printed by --dry-run."""
    return [(p, t, law_tok_per_s(p)) for p, t in ANCHORS]


def est_tok_per_s(n_params: int, tokens_per_step: int) -> tuple[float, float]:
    """(fast, slow) tok/s estimates: compute-bound law, launch-bound ceiling."""
    fast = law_tok_per_s(n_params)
    slow = min(fast, CEILING_STEPS_PER_S * tokens_per_step)
    return fast, slow


def tokens_per_run(unique_tokens: int, n_epochs: int, seq_len: int,
                   batch_size: int, n_canary: int = 8,
                   canary_repeats: int = 4) -> int:
    """Tokens actually stepped on, matching epoch_loader's drop-remainder rule.

    plant_canaries grows the pool by n_canary * canary_repeats * seq_len tokens
    before training, and epoch_loader drops the trailing partial chunk and the
    trailing partial batch, so the budget a cell really costs is neither U nor
    U * n_epochs exactly.
    """
    pool = unique_tokens + n_canary * canary_repeats * seq_len
    n_chunks = pool // seq_len
    n_batches = n_chunks // batch_size
    return n_epochs * n_batches * batch_size * seq_len


def run_hours(total_tokens: int, tok_per_s: float) -> float:
    return total_tokens / tok_per_s / 3600.0


def format_eta(label: str, n_runs: int, hours_fast: float,
               hours_slow: float) -> str:
    lo, hi = GPU4090_SPEEDUP
    return (f"  {label:<28} runs={n_runs:>4}  "
            f"GPU-h(4080S) {hours_fast:6.2f}-{hours_slow:6.2f}  "
            f"[4090 ~{hours_fast/hi:5.2f}-{hours_slow/lo:5.2f} h]")


# ---------------------------------------------------------------------------
# Cell-list plumbing (resume, sharding by substring, manifest)
# ---------------------------------------------------------------------------
def already_done(path: str) -> bool:
    """True iff the jsonl exists and ends with a _summary line (in its tail)."""
    if not os.path.exists(path):
        return False
    with open(path, "rb") as fh:
        fh.seek(0, 2)
        size = fh.tell()
        if size == 0:
            return False
        fh.seek(max(0, size - 4096))
        tail = fh.read().decode("utf-8", errors="replace")
    return '"_summary"' in tail


def filter_cells(cells, only: str | None):
    if not only:
        return list(cells)
    return [(name, ov) for name, ov in cells if only in name]


def write_manifest(out_dir: str, arm: str, cells, meta: dict) -> str:
    """Record every PLANNED run (unsharded) so retrieval can be completeness-checked."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "MANIFEST.json")
    payload = {
        "arm": arm,
        "written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_runs": len(cells),
        "out_dir": os.path.abspath(out_dir),
        **meta,
        "runs": [{"name": name, "file": name + ".jsonl", "config": ov}
                 for name, ov in cells],
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=1, default=str)
    return path


def preselect_gpu(argv: list[str] | None = None) -> str | None:
    """Honor --gpu N by setting CUDA_VISIBLE_DEVICES BEFORE torch initializes.

    Must be called before the first `import torch` in the process, hence the
    manual argv scan (argparse runs long after the runner's imports).
    """
    argv = list(sys.argv if argv is None else argv)
    for i, a in enumerate(argv):
        val = None
        if a == "--gpu" and i + 1 < len(argv):
            val = argv[i + 1]
        elif a.startswith("--gpu="):
            val = a.split("=", 1)[1]
        if val is not None:
            os.environ["CUDA_VISIBLE_DEVICES"] = val
            return val
    return os.environ.get("CUDA_VISIBLE_DEVICES")


def add_common_args(ap) -> None:
    ap.add_argument("--smoke", action="store_true",
                    help="CPU end-to-end smoke (tiny cells, temp files) and exit")
    ap.add_argument("--pilot", action="store_true",
                    help="Run the smallest complete sub-grid (first seed only)")
    ap.add_argument("--full", action="store_true",
                    help="Run the full planned grid (default when training)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print cells + GPU-hour estimates and exit (no training)")
    ap.add_argument("--probe", action="store_true",
                    help="Measure real tok/s per capacity on the visible GPU and exit")
    ap.add_argument("--only", default=None,
                    help="Run only cells whose name contains this substring")
    ap.add_argument("--gpu", default=None,
                    help="CUDA device id for this worker (sets CUDA_VISIBLE_DEVICES)")


# ---------------------------------------------------------------------------
# jsonl contract + smoke helpers
# ---------------------------------------------------------------------------
def read_jsonl(path: str) -> tuple[dict, list[dict], dict]:
    """(meta, per-step records, summary) from a house-format jsonl."""
    meta, recs, summary = {}, [], {}
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if "_meta" in r:
                meta = r["_meta"]
            elif "_summary" in r:
                summary = r["_summary"]
            else:
                recs.append(r)
    return meta, recs, summary


def verify_house_format(path: str, required_meta: tuple[str, ...] = ()) -> dict:
    """Assert the _meta-first / per-step / _summary-last contract; return summary."""
    meta, recs, summary = read_jsonl(path)
    assert meta, f"{path}: missing _meta record"
    assert summary, f"{path}: missing _summary record"
    assert recs, f"{path}: no per-epoch records"
    for k in ("epoch", "tokens_seen", "train_loss", "val_loss", "canary_gap"):
        assert k in recs[0], f"{path}: per-epoch record missing {k!r}"
    for k in required_meta:
        assert k in meta, f"{path}: _meta missing {k!r}"
    with open(path) as f:
        first = json.loads(next(l for l in f if l.strip()))
    assert "_meta" in first, f"{path}: first record is not _meta"
    return summary


def limit_cpu_threads(default: int = 2) -> int:
    """Pin torch's CPU thread pool for the smoke gate.

    The smoke models are tiny, so on a busy machine the default pool (one worker
    per core) spends all its time in contention: measured 5.4 s/step at 24
    threads vs 0.03 s/step at 2 for the same tiny cell. Override with
    E1_SMOKE_THREADS. Smoke-only; the GPU path never calls this.
    """
    import torch  # noqa: E402

    n = int(os.environ.get("E1_SMOKE_THREADS", default))
    torch.set_num_threads(n)
    return n


def param_count(capacity: str, vocab: int = 256, seq_len: int = 128) -> int:
    """Instantiate a preset on CPU purely to report its exact parameter count."""
    from model import build_lm, count_params  # noqa: E402  (lazy: needs torch)
    m = build_lm(vocab_size=vocab, seq_len=seq_len, capacity=capacity,
                 mlp_ratio=4, init_scale=1.0, device="cpu")
    n = count_params(m)
    del m
    return n


def one_step_check(capacity: str, vocab: int = 256, seq_len: int = 128,
                   batch: int = 2) -> tuple[int, float]:
    """One real forward+backward+step at a preset (tiny batch, CPU-affordable).

    Exercises the expensive capacity presets end-to-end without paying for a
    full run, so the smoke covers the exact model the GPU round will train.
    """
    import torch  # noqa: E402
    from train_repeat import Config, build_model, build_optimizer, \
        _ce_full_sequence  # noqa: E402

    cfg = Config(capacity=capacity, vocab=vocab, seq_len=seq_len,
                 batch_size=batch, device="cpu")
    torch.manual_seed(0)
    model = build_model(cfg, "cpu")
    n = sum(p.numel() for p in model.parameters())
    opts = build_optimizer(model, cfg)
    xb = torch.randint(0, vocab, (batch, seq_len))
    loss = _ce_full_sequence(model, xb)
    for opt in opts:
        opt.zero_grad(set_to_none=True)
    loss.backward()
    for opt in opts:
        opt.step()
    val = float(loss.item())
    del model, opts
    return n, val


def probe_tok_per_s(capacities, vocab: int = 256, seq_len: int = 128,
                    batch: int = 32, steps: int = 200) -> list[dict]:
    """Measured throughput per capacity on the visible device (GPU round only)."""
    import torch  # noqa: E402
    from train_repeat import Config, build_model, build_optimizer, \
        _ce_full_sequence  # noqa: E402

    device = "cuda" if torch.cuda.is_available() else "cpu"
    rows = []
    for cap in capacities:
        cfg = Config(capacity=cap, vocab=vocab, seq_len=seq_len,
                     batch_size=batch, device=device)
        torch.manual_seed(0)
        model = build_model(cfg, device)
        n = sum(p.numel() for p in model.parameters())
        opts = build_optimizer(model, cfg)
        xb = torch.randint(0, vocab, (batch, seq_len), device=device)

        def _step():
            loss = _ce_full_sequence(model, xb)
            for opt in opts:
                opt.zero_grad(set_to_none=True)
            loss.backward()
            for opt in opts:
                opt.step()

        for _ in range(10):
            _step()
        if device == "cuda":
            torch.cuda.synchronize()
        t0 = time.time()
        for _ in range(steps):
            _step()
        if device == "cuda":
            torch.cuda.synchronize()
        dt = time.time() - t0
        tps = steps * batch * seq_len / dt
        rows.append({"capacity": cap, "n_params": n, "tok_per_s": tps,
                     "ms_per_step": dt / steps * 1000.0,
                     "law_tok_per_s": law_tok_per_s(n), "device": device})
        del model, opts, xb
        if device == "cuda":
            torch.cuda.empty_cache()
    return rows
