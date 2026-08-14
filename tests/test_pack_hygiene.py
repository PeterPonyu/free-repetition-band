"""Zenodo pack + site artifact hygiene (I1, I4, I5b, U5, F9)."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from conftest import REPO_ROOT


def test_pack_script_excludes_github_portal_and_site() -> None:
    script = (REPO_ROOT / "pack_zenodo_tarball.sh").read_text(encoding="utf-8")
    assert ".github" in script
    assert "portal" in script
    assert "_site" in script
    assert "out" in script


def test_gitattributes_export_ignore_website_trees() -> None:
    attrs = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "portal/ export-ignore" in attrs
    assert "_site/ export-ignore" in attrs
    assert "out/ export-ignore" in attrs
    assert ".github/ export-ignore" in attrs


def test_gitignore_excludes_site_output() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "_site/" in gitignore
    assert "out/" in gitignore


def test_build_script_is_copy_and_validate() -> None:
    build = REPO_ROOT / "portal" / "build.sh"
    assert build.is_file()
    text = build.read_text(encoding="utf-8")
    assert "latexmk" not in text.lower()
    assert "FIGURE-INDEX" in text
    assert "npm run build" in text
    assert "experiments/" not in text or "leaked" in text
    assert "cp -a experiments" not in text


def test_build_resolves_site_data_paths() -> None:
    subprocess.run(["bash", "portal/build.sh"], cwd=REPO_ROOT, check=True)
    site = REPO_ROOT / "out"
    assert (site / "index.html").is_file()
    assert (site / "onset" / "index.html").is_file()
    assert (site / "data" / "figures.json").is_file()
    assert not (site / "data" / "figs").exists()
    public = (site / "data" / "figures.json").read_text(encoding="utf-8")
    assert "E1_scale_band" in public
    assert "caption" not in public
    assert "venue_flat_name" not in public
    assert "R_free" not in public
    assert "Figure1.pdf" not in public
    assert not (site / "experiments").exists()
    assert not list(site.rglob("*.pdf"))
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "manuscript.pdf" not in html
    assert "/free-repetition-band/" in html


def test_workdir_pack_omits_portal_site_github() -> None:
    script = REPO_ROOT / "pack_zenodo_tarball.sh"
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "pack.tar.gz"
        env = os.environ.copy()
        subprocess.run(
            ["bash", str(script), "--from-workdir", "--out", str(out)],
            cwd=REPO_ROOT,
            check=True,
            env=env,
        )
        members = subprocess.run(
            ["tar", "-tzf", str(out)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        joined = "\n".join(members)
        assert "/portal/" not in joined and not any(
            part == "portal" for line in members for part in line.split("/")
        )
        assert "/_site/" not in joined
        assert "/out/" not in joined and not any(
            part == "out" for line in members for part in line.split("/")
        )
        assert "/.github/" not in joined
        assert any("papers/E1/main.tex" in line for line in members)
