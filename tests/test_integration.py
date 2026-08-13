"""Integration: copy+validate portal build, no latexmk, artifact hygiene (I1, I4)."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path


def test_portal_build_script_is_executable(repo_root: Path) -> None:
    script = repo_root / "portal" / "build.sh"
    assert script.is_file(), "portal/build.sh must exist"
    mode = script.stat().st_mode
    assert mode & stat.S_IXUSR, "portal/build.sh must be executable"


def test_portal_build_script_validates_index_and_does_not_run_latexmk(
    repo_root: Path,
) -> None:
    script = (repo_root / "portal" / "build.sh").read_text(encoding="utf-8")
    assert "FIGURE-INDEX.json" in script
    assert "latexmk" not in script
    assert "pdflatex" not in script
    assert "lualatex" not in script


def test_portal_build_copies_portal_to_site_without_experiments(repo_root: Path) -> None:
    site = repo_root / "_site"
    if site.exists():
        shutil.rmtree(site)
    subprocess.run(
        ["bash", str(repo_root / "portal" / "build.sh")],
        cwd=repo_root,
        check=True,
        env={**os.environ, "SITE_DIR": str(site)},
    )
    assert (site / "index.html").is_file()
    assert not (site / "experiments").exists()
    assert not (site / ".omc").exists()
    data = site / "data"
    assert (data / "FIGURE-INDEX.json").is_file() or (data / "figures.json").is_file()
    assert list(site.rglob("main.pdf")) == []
    assert list(site.rglob("manuscript.pdf")) == []
