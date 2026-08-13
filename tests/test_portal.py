"""Portal uniqueness and consumption checks for the E1 field-guide stub (P-E1, U1–U6)."""

from __future__ import annotations

import re
from pathlib import Path

EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF]")


def _portal_text(repo_root: Path) -> str:
    portal = repo_root / "portal"
    assert portal.is_dir(), "portal/ must exist"
    chunks: list[str] = []
    for path in sorted(portal.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".html", ".css", ".js", ".svg"}:
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def test_portal_has_no_shared_theme_package(repo_root: Path) -> None:
    # Paper-local CSS is allowed; a shared portal-theme package is not.
    assert not (repo_root / "portal-theme").exists()
    assert not any(repo_root.glob("**/portal-theme/**"))


def test_portal_index_uses_field_guide_landmark(repo_root: Path) -> None:
    html = (repo_root / "portal" / "index.html").read_text(encoding="utf-8")
    assert "field-guide" in html
    assert "instrument" not in html
    assert "class=\"console\"" not in html
    assert "class='console'" not in html
    assert "notebook" not in html
    assert "atlas" not in html.lower()


def test_portal_declares_fraunces_and_atkinson_hyperlegible(repo_root: Path) -> None:
    text = _portal_text(repo_root)
    assert "Fraunces" in text
    assert "Atkinson Hyperlegible" in text


def test_portal_nav_includes_band_onset_capacity(repo_root: Path) -> None:
    html = (repo_root / "portal" / "index.html").read_text(encoding="utf-8")
    for label in ("Band", "Onset", "Capacity"):
        assert label in html


def test_portal_nav_is_not_instrument_or_console_chrome(repo_root: Path) -> None:
    html = (repo_root / "portal" / "index.html").read_text(encoding="utf-8")
    assert "Nomogram" not in html
    assert ">Cap<" not in html and ">Dose<" not in html


def test_portal_has_no_emoji(repo_root: Path) -> None:
    text = _portal_text(repo_root)
    assert EMOJI_RE.search(text) is None


def test_portal_footer_lists_concept_doi_github_and_dual_license(repo_root: Path) -> None:
    html = (repo_root / "portal" / "index.html").read_text(encoding="utf-8")
    assert "10.5281/zenodo.21020378" in html
    assert "github.com/PeterPonyu/free-repetition-band" in html
    assert "MIT" in html
    assert "CC BY" in html


def test_portal_does_not_ship_live_journal_pdf(repo_root: Path) -> None:
    portal = repo_root / "portal"
    forbidden = list(portal.rglob("main.pdf")) + list(portal.rglob("manuscript.pdf"))
    assert forbidden == []


def test_portal_consumes_figure_index_not_peerj_figure_paths(repo_root: Path) -> None:
    text = _portal_text(repo_root)
    assert "FIGURE-INDEX.json" in text or "figures.json" in text
    assert "Figure3.pdf" not in text
    assert "Figure8.pdf" not in text
