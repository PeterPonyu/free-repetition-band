"""Portal uniqueness and consumption contract (P-E1, U1–U7)."""

from __future__ import annotations

import re

from conftest import (
    FORBIDDEN_A,
    FORBIDDEN_A_NAV,
    FORBIDDEN_B,
    FORBIDDEN_B_NAV,
    FORBIDDEN_C,
    FORBIDDEN_C_NAV,
    FORBIDDEN_E2,
    FORBIDDEN_E2_NAV,
    GITHUB_URL,
    INDEX_HINTS,
    PIPELINE_POINTER,
    PORTAL_DIR,
    PORTAL_INDEX,
    REQUIRED_FONTS,
    REQUIRED_NAV,
    REQUIRED_NAV_SUBSET,
    REQUIRED_SUMMARIES,
    CONCEPT_DOI,
    portal_corpus,
)

STUB_RE = re.compile(
    r"CI stub|instrument stub|Two-probe contract stub|waits on a user-approved reference\.png|\bstub\b",
    re.I,
)
ABSOLUTE_ASSET_RE = re.compile(
    r"""(?:href|src)\s*=\s*["']/(?!/)[^"']+|url\(\s*/(?!/)"""
)


def test_portal_index_exists() -> None:
    assert PORTAL_INDEX.is_file()


def test_field_guide_landmark() -> None:
    html = portal_corpus()
    lower = html.lower()
    landmark = (
        re.search(r"<article[^>]*\bfield-guide\b", html, re.I) is not None
        or 'class="field-guide"' in html
        or 'data-layout="field-guide"' in html
    )
    assert landmark, "P-E1: expected article.field-guide landmark"
    assert "stratum" in lower or "epoch-band" in lower or "band plate" in lower
    assert "status-strip" not in lower
    assert "three-pane" not in lower
    assert "notebook gutter" not in lower
    assert "main.atlas" not in html


def test_type_stack_fraunces_and_atkinson() -> None:
    text = portal_corpus()
    for font in REQUIRED_FONTS:
        assert font in text, f"missing typeface {font}"


def test_chapter_list_nav_labels() -> None:
    text = portal_corpus()
    for label in REQUIRED_NAV_SUBSET:
        assert re.search(rf"\b{re.escape(label)}\b", text)
    missing = [label for label in REQUIRED_NAV if not re.search(rf"\b{re.escape(label)}\b", text)]
    assert not missing, f"chapter-list missing {missing}"


def test_consumes_figure_index_and_summaries() -> None:
    text = portal_corpus()
    assert any(hint in text for hint in INDEX_HINTS)
    for name in REQUIRED_SUMMARIES:
        assert name in text, f"portal must cite {name}"


def test_points_at_zenodo_pipeline_github() -> None:
    text = portal_corpus()
    assert CONCEPT_DOI in text
    assert PIPELINE_POINTER in text or "PIPELINE.md" in text
    assert GITHUB_URL in text


def test_footer_license_doi_github() -> None:
    text = portal_corpus()
    lower = text.lower()
    assert "mit" in lower and ("cc by" in lower or "cc-by" in lower)
    assert CONCEPT_DOI in text
    assert GITHUB_URL in text


def test_no_venue_pdf_paths() -> None:
    text = portal_corpus()
    assert "papers/peerj-E1/upload" not in text
    assert not re.search(r"Figure(?:1[0-2]|[1-9])\.pdf", text)
    assert "manuscript.pdf" not in text
    assert "main.pdf" not in text.lower() or "main.pdf" not in text


def test_no_emoji_slop() -> None:
    text = portal_corpus()
    assert re.search(r"[\U0001F300-\U0001FAFF]", text) is None


def test_anti_stub() -> None:
    text = portal_corpus()
    assert STUB_RE.search(text) is None, "U-STUB: portal still contains stub copy"


def test_not_paper_a_dashboard() -> None:
    text = portal_corpus()
    for token in FORBIDDEN_A:
        assert token.lower() not in text.lower(), f"looks like Paper A: {token}"
    for label in FORBIDDEN_A_NAV:
        assert not re.search(rf"\b{label}\b", text), f"A nav leaked: {label}"


def test_not_paper_b_atlas() -> None:
    text = portal_corpus()
    for token in FORBIDDEN_B:
        assert token.lower() not in text.lower()
    for label in FORBIDDEN_B_NAV:
        assert not re.search(rf"\b{label}\b", text)


def test_not_paper_c_notebook() -> None:
    text = portal_corpus()
    for token in FORBIDDEN_C:
        assert token.lower() not in text.lower()
    for label in FORBIDDEN_C_NAV:
        assert not re.search(rf"\b{label}\b", text)


def test_not_paper_e2_console() -> None:
    text = portal_corpus()
    for token in FORBIDDEN_E2:
        assert token.lower() not in text.lower()
    for label in FORBIDDEN_E2_NAV:
        assert not re.search(rf"\b{label}\b", text)


def test_no_shared_theme_package() -> None:
    assert PORTAL_DIR.is_dir()
    assert not (PORTAL_DIR / "portal-theme").exists()
    assert not list(PORTAL_DIR.rglob("tokens.css"))


def test_no_journal_pdf_in_portal_tree() -> None:
    pdfs = list(PORTAL_DIR.rglob("*.pdf"))
    assert not pdfs, f"portal must not host PDFs: {pdfs}"


def test_relative_only_asset_urls() -> None:
    text = portal_corpus()
    assert "/assets" not in text
    assert ABSOLUTE_ASSET_RE.search(text) is None, "U7: root-absolute asset URL"
    assert 'href="/' not in text
    assert 'src="/' not in text
    assert "url(/" not in text
