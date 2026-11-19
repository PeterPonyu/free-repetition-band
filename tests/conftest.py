"""Warehouse-root fixtures for Paper E1 contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "papers" / "FIGURE-INDEX.json"
SCHEMA_PATH = REPO_ROOT / "papers" / "FIGURE-INDEX.schema.json"
PORTAL_DIR = REPO_ROOT / "portal"
PORTAL_INDEX = PORTAL_DIR / "app" / "page.tsx"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
SKIP_DIR_NAMES = {".next", "node_modules", "out", "public"}

CONCEPT_DOI = "10.5281/zenodo.21020378"
VERSION_DOI = "10.5281/zenodo.24341844"
GITHUB_REPO = "PeterPonyu/free-repetition-band"
GITHUB_URL = f"https://github.com/{GITHUB_REPO}"
PIPELINE_POINTER = "papers/figs/PIPELINE.md"

REQUIRED_FONTS = ("Fraunces", "Atkinson Hyperlegible")
REQUIRED_NAV = ("Band", "Onset", "Capacity", "Exposure", "Scale", "Reproduce-as-rebuild")
REQUIRED_NAV_SUBSET = ("Band", "Onset", "Capacity")
SCIENCE_CHAPTERS = ("band", "onset", "capacity", "exposure", "scale")
SCIENCE_ASKS = (
    "How does the free band vary with capacity?",
    "How does repeated-data value decay?",
    "Is the free band capacity-invariant?",
    "Does the free band remain invariant?",
    "How does loss behave on real bytes?",
)
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


SOURCE_SUFFIXES = {".html", ".css", ".js", ".mjs", ".ts", ".tsx", ".svg"}


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


def portal_source_files() -> list[Path]:
    assert PORTAL_DIR.is_dir(), f"missing portal at {PORTAL_DIR}"
    files: list[Path] = []
    for path in sorted(PORTAL_DIR.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() in SOURCE_SUFFIXES:
            files.append(path)
    return files


def portal_corpus() -> str:
    chunks = [
        path.read_text(encoding="utf-8", errors="replace")
        for path in portal_source_files()
    ]
    assert chunks, f"no portal source under {PORTAL_DIR}"
    return "\n".join(chunks)


EXPORT_TEXT_SUFFIXES = {".html", ".js", ".css", ".json", ".svg", ".txt", ".xml"}


def export_corpus() -> str:
    out = REPO_ROOT / "out"
    assert out.is_dir(), "missing Next.js export at out/"
    chunks: list[str] = []
    for path in sorted(out.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in EXPORT_TEXT_SUFFIXES:
            continue
        chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    assert chunks, "no text files in out/"
    return "\n".join(chunks)


def workflow_path(name: str) -> Path:
    return WORKFLOWS_DIR / name
