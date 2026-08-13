"""Freeze / independence / lab-tree guards (G2, Z1–Z5)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from conftest import PORTAL_DIR, REPO_ROOT, WAREHOUSE_TEX, portal_corpus

LAB = Path("/home/zeyufu/Desktop/dl-research")


def test_readme_cites_github() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://github.com/PeterPonyu/free-repetition-band" in readme


def test_no_compiled_manuscript_in_portal_or_site() -> None:
    for root in (PORTAL_DIR, REPO_ROOT / "_site", REPO_ROOT / "out"):
        if not root.exists():
            continue
        pdfs = list(root.rglob("*.pdf"))
        assert not pdfs
        for name in ("main.pdf", "manuscript.pdf"):
            assert not (root / name).is_file()


def test_pointer_tex_is_full_manuscript() -> None:
    lines = WAREHOUSE_TEX.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 2000


def test_no_suite_chrome_across_five_papers() -> None:
    html = portal_corpus()
    assert "muon-norm-cap-grokking" not in html
    assert "grokking-clock" not in html
    assert "architecture-staircase" not in html
    assert "calibration-traps" not in html


def test_lab_papers_tree_untouched() -> None:
    if not (LAB / ".git").is_dir():
        return
    proc = subprocess.run(
        ["git", "diff", "--", "papers/"],
        cwd=LAB,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout == "", proc.stdout
