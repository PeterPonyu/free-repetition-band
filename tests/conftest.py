"""Warehouse-root fixtures for Paper E1 contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "papers" / "FIGURE-INDEX.json"
SCHEMA_PATH = REPO_ROOT / "papers" / "FIGURE-INDEX.schema.json"
LAB_SCHEMA = Path("/home/zeyufu/Desktop/dl-research/.omx/plans/figure-index.schema.json")
CANONICAL_TEX = Path("/home/zeyufu/Desktop/dl-research/papers/E1/main.tex")
WAREHOUSE_TEX = REPO_ROOT / "papers" / "E1" / "main.tex"
PORTAL_DIR = REPO_ROOT / "portal"
PORTAL_INDEX = PORTAL_DIR / "index.html"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

CONCEPT_DOI = "10.5281/zenodo.21020378"
VERSION_DOI = "10.5281/zenodo.21020379"
GITHUB_REPO = "PeterPonyu/free-repetition-band"
GITHUB_URL = f"https://github.com/{GITHUB_REPO}"
PIPELINE_POINTER = "papers/figs/PIPELINE.md"

REQUIRED_FONTS = ("Fraunces", "Atkinson Hyperlegible")
REQUIRED_NAV = ("Band", "Onset", "Capacity", "Exposure", "Scale", "Reproduce")
REQUIRED_NAV_SUBSET = ("Band", "Onset", "Capacity")
REQUIRED_SUMMARIES = ("E1_scale_band", "E1_repeat", "E1_capxl")
INDEX_HINTS = ("FIGURE-INDEX.json", "data/figures.json")
YAML_OR_SCHEMATIC = {
    "E1_landscape",
    "E1_scheme",
    "E1_repeat",
    "E1_large_completion",
    "E1_capxl",
    "E1_grid",
    "E1_scale",
    "E1_scale_band",
    "E1_capacity_bridge",
    "E1_case",
    "E1_within_run",
    "E1_exposure_control",
}

FORBIDDEN_A = ("status-strip", "instrument-chrome", "IBM Plex")
FORBIDDEN_A_NAV = ("Cap", "Dose", "Floor", "LMC")
FORBIDDEN_B = ("regime-map", "isobar", "Source Serif 4")
FORBIDDEN_B_NAV = ("Regimes", "Slopes", "EOS")
FORBIDDEN_C = ("notebook-gutter", "freeze-probe", "Literata")
FORBIDDEN_C_NAV = ("Probes", "Staircase", "Subspace")
FORBIDDEN_E2 = ("three-pane", "detector-console", "JetBrains Mono")
FORBIDDEN_E2_NAV = ("Nomogram", "BIG-Bench", "Preflight")


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


def portal_corpus() -> str:
    assert PORTAL_DIR.is_dir(), f"missing portal at {PORTAL_DIR}"
    chunks: list[str] = []
    for path in sorted(PORTAL_DIR.rglob("*")):
        if path.suffix.lower() in {".html", ".css", ".js", ".svg"}:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    assert chunks, f"no HTML/CSS/JS under {PORTAL_DIR}"
    return "\n".join(chunks)


def workflow_path(name: str) -> Path:
    return WORKFLOWS_DIR / name
