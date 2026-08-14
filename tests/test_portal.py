"""Portal uniqueness, Next.js export, leak audit (P-E1, U1–U7)."""

from __future__ import annotations

import json
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
    PORTAL_DIR,
    PORTAL_INDEX,
    REPO_ROOT,
    REQUIRED_FONTS,
    REQUIRED_NAV,
    REQUIRED_NAV_SUBSET,
    SCIENCE_ASKS,
    SCIENCE_CHAPTERS,
    CONCEPT_DOI,
    export_corpus,
    portal_corpus,
    portal_source_files,
)

STUB_RE = re.compile(
    r"CI stub|instrument stub|Two-probe contract stub|waits on a user-approved reference\.png|\bstub\b",
    re.I,
)
LEAK_RE = re.compile(
    r"R_free|R_\{free\}|R<sub>free|218 runs|WikiText|20M-token|"
    r"Figure(?:1[0-2]|[1-9])\.pdf|manuscript\.pdf|"
    r"nearly free for four|copied-canary|8/9 cells|"
    r"4–10 epoch|4-10 epoch|4–10 free|R_free 4",
    re.I,
)
CHROME_RE = re.compile(
    r"\bdocuments?\b|\bpapers?\b|\bjournals?\b|\bmanuscripts?\b|"
    r"\bsubmissions?\b|PeerJ|Figure(?:1[0-2]|[1-9])(?:\.pdf)?|"
    r"main\.tex|FIGURE-INDEX|\bPIPELINE\b|\bwarehouse\b",
    re.I,
)
CODE_RE = re.compile(
    r"\bE1_|\bE1\b|FIGURE-INDEX|PIPELINE\.md|figs/summaries|"
    r"papers/E1|venue_flat_name",
    re.I,
)


def test_portal_index_exists() -> None:
    assert PORTAL_INDEX.is_file()
    assert (PORTAL_DIR / "next.config.mjs").is_file()
    assert not (PORTAL_DIR / "index.html").exists(), "static index.html dump must be gone"


def test_next_export_and_base_path() -> None:
    config = (PORTAL_DIR / "next.config.mjs").read_text(encoding="utf-8")
    assert "output: \"export\"" in config or "output: 'export'" in config
    assert "/free-repetition-band" in config
    pages = (REPO_ROOT / ".github" / "workflows" / "pages.yml").read_text(
        encoding="utf-8"
    )
    assert "path: out" in pages


def test_field_guide_landmark() -> None:
    html = portal_corpus()
    lower = html.lower()
    landmark = (
        re.search(r"<article[^>]*\bfield-guide\b", html, re.I) is not None
        or 'className="field-guide"' in html
        or 'class="field-guide"' in html
        or 'data-layout="field-guide"' in html
    )
    assert landmark, "P-E1: expected article.field-guide landmark"
    assert "stratum" in lower or "epoch-band" in lower
    assert "status-strip" not in lower
    assert "three-pane" not in lower
    assert "notebook gutter" not in lower
    assert "main.atlas" not in html


def test_type_stack_fraunces_and_atkinson() -> None:
    text = portal_corpus()
    fonts = (PORTAL_DIR / "app" / "fonts.ts").read_text(encoding="utf-8")
    # C8: self-hosted woff2 via next/font/local; the build must never fetch fonts.
    assert "next/font/local" in fonts
    assert "next/font/google" not in fonts
    assert "--font-display" in fonts
    assert "--font-body" in fonts
    for font in REQUIRED_FONTS:
        slug = font.lower().replace(" ", "-")
        assert slug in fonts.lower() or font in text
    fonts_dir = PORTAL_DIR / "app" / "fonts"
    woff2 = sorted(fonts_dir.glob("*.woff2"))
    assert woff2, "C8: committed woff2 files required"
    for src in re.findall(r'path:\s*"./fonts/([^"]+)"', fonts):
        assert (fonts_dir / src).is_file(), f"C8: missing font file {src}"
    assert list(fonts_dir.glob("OFL-*.txt")), "C8: OFL license text required"


def test_chapter_list_nav_labels() -> None:
    text = portal_corpus()
    for label in REQUIRED_NAV_SUBSET:
        assert re.search(rf"\b{re.escape(label)}\b", text)
    missing = [label for label in REQUIRED_NAV if not re.search(rf"\b{re.escape(label)}\b", text)]
    assert not missing, f"chapter-list missing {missing}"
    nav = (PORTAL_DIR / "app" / "ChapterNav.tsx").read_text(encoding="utf-8")
    assert "usePathname" in nav
    assert "Link" in nav


def test_renders_stratum_science() -> None:
    science = (PORTAL_DIR / "lib" / "science.ts").read_text(encoding="utf-8")
    assert "bedFor" in science
    assert "figures.json" in science
    payload = json.loads((PORTAL_DIR / "public" / "data" / "figures.json").read_text(encoding="utf-8"))
    beds = payload.get("beds") or []
    chapters = {bed["chapter"] for bed in beds}
    assert set(SCIENCE_CHAPTERS) <= chapters
    for bed in beds:
        blob = json.dumps(bed)
        assert bed.get("asks"), f"missing asks for {bed.get('chapter')}"
        assert CODE_RE.search(blob) is None, f"code leak in bed {bed.get('chapter')}"
        assert "caption" not in bed
        assert "summary" not in bed
    for ask in SCIENCE_ASKS:
        assert any(ask in (bed.get("asks") or []) for bed in beds), ask


def test_points_at_zenodo_and_github() -> None:
    text = portal_corpus()
    assert CONCEPT_DOI in text
    assert GITHUB_URL in text
    assert "Reproduce-as-rebuild" in text


def test_no_document_chrome() -> None:
    """Visible door copy is the scientific object, not venue chrome."""
    for path in portal_source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        hit = CHROME_RE.search(text)
        assert hit is None, (
            f"chrome in {path.relative_to(PORTAL_DIR)}: {hit.group(0)!r}"
        )
        code = CODE_RE.search(text)
        assert code is None, (
            f"code name in {path.relative_to(PORTAL_DIR)}: {code.group(0)!r}"
        )


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


def test_no_paper_finding_leak() -> None:
    for path in portal_source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        hit = LEAK_RE.search(text)
        assert hit is None, f"leak in {path.relative_to(PORTAL_DIR)}: {hit.group(0)!r}"


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
    pdfs = [
        path
        for path in PORTAL_DIR.rglob("*.pdf")
        if not any(part in {".next", "node_modules"} for part in path.parts)
    ]
    assert not pdfs, f"portal must not host PDFs: {pdfs}"


def test_base_path_not_user_site_assets() -> None:
    text = portal_corpus()
    assert "/assets" not in text
    assert 'href="/assets' not in text
    config = (PORTAL_DIR / "next.config.mjs").read_text(encoding="utf-8")
    assert 'basePath: "/free-repetition-band"' in config


def test_export_html_uses_base_path_and_has_no_leaks() -> None:
    out_index = REPO_ROOT / "out" / "index.html"
    if not out_index.is_file():
        import subprocess

        subprocess.run(["bash", "portal/build.sh"], cwd=REPO_ROOT, check=True)
    html = export_corpus()
    assert "/free-repetition-band/" in html
    assert LEAK_RE.search(html) is None
    assert "Band" in html and "Onset" in html
    assert "Reproduce-as-rebuild" in html
    assert "Fraunces" in html or "--font-display" in html or "font" in html.lower()
    html_copy = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted((REPO_ROOT / "out").rglob("*.html"))
    )
    assert CHROME_RE.search(html_copy) is None, "export HTML still has venue chrome"
    assert CODE_RE.search(html_copy) is None, "export HTML still has code names"
    for ask in SCIENCE_ASKS:
        assert ask in html_copy, f"export missing science ask: {ask}"
    assert not (REPO_ROOT / "out" / "data" / "figs" / "summaries").exists()
    public_index = REPO_ROOT / "out" / "data" / "figures.json"
    assert public_index.is_file()
    text = public_index.read_text(encoding="utf-8")
    assert "caption" not in text
    assert "venue_flat_name" not in text
    assert "E1_" not in text
    assert LEAK_RE.search(text) is None
    assert CODE_RE.search(text) is None
