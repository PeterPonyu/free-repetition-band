"""Figure-pointer contract (test-spec F1–F9, F6b) for free-repetition-band."""

from __future__ import annotations

import json
import re
import subprocess

import jsonschema

from conftest import (
    CANONICAL_TEX,
    INDEX_PATH,
    LAB_SCHEMA,
    REPO_ROOT,
    SCHEMA_PATH,
    WAREHOUSE_TEX,
    YAML_OR_SCHEMATIC,
)

PEERJ_INCLUDE = re.compile(r"\\includegraphics\{[^}]*Figure(?:1[0-2]|[1-9])\.pdf")
SCHEMATIC_IDS = {"E1_landscape", "E1_scheme"}


def _index() -> dict:
    assert INDEX_PATH.is_file(), f"F1: missing {INDEX_PATH}"
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def test_figure_index_exists() -> None:
    assert INDEX_PATH.is_file()


def test_figure_index_schema_file_exists() -> None:
    assert SCHEMA_PATH.is_file(), f"F1: schema missing at {SCHEMA_PATH}"


def test_schema_is_byte_identical_to_lab_ssot() -> None:
    if LAB_SCHEMA is None or not LAB_SCHEMA.is_file():
        return
    assert SCHEMA_PATH.read_bytes() == LAB_SCHEMA.read_bytes(), (
        "F1: warehouse FIGURE-INDEX.schema.json must match lab SSOT"
    )


def test_schema_paper_id_is_enum_not_const() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    paper_id = schema["properties"]["paper_id"]
    assert "const" not in paper_id
    assert set(paper_id["enum"]) == {"A", "B", "C", "E1", "E2"}


def test_figure_index_validates_against_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=_index(), schema=schema)


def test_index_identifies_paper_e1_warehouse() -> None:
    data = _index()
    assert data["paper_id"] == "E1"
    assert data["github"] == "PeterPonyu/free-repetition-band"
    assert data["zenodo_concept_doi"] == "10.5281/zenodo.21020378"
    assert data["pipeline"].startswith("figs/")


def test_index_ids_are_yaml_or_schematic() -> None:
    data = _index()
    for fig in data["figures"]:
        fig_id = fig["id"]
        assert fig_id in YAML_OR_SCHEMATIC, f"F2: unknown id {fig_id}"
        generator = fig.get("generator")
        if generator:
            assert generator.startswith("figs/"), f"F9: generator must be papers/-relative: {generator}"
            gen_path = REPO_ROOT / "papers" / generator
            assert gen_path.is_file(), f"F2: generator missing for {fig_id}: {gen_path}"
        elif fig_id in SCHEMATIC_IDS:
            raise AssertionError(f"F2: schematic {fig_id} needs a generator pointer")


def test_index_path_grammar_is_papers_relative() -> None:
    data = _index()
    for fig in data["figures"]:
        for key in ("generator", "summary", "preview_svg", "tex_build", "vec_build"):
            value = fig.get(key)
            if value is None:
                continue
            assert value.startswith("figs/"), f"F9: {fig['id']}.{key}={value!r} must start with figs/"
            assert not value.startswith("summaries/"), f"F9: mixed base in {fig['id']}.{key}"


def test_summaries_and_previews_resolve_or_are_null() -> None:
    data = _index()
    missing: list[str] = []
    for fig in data["figures"]:
        for key in ("summary", "preview_svg"):
            value = fig.get(key)
            if not value:
                continue
            path = REPO_ROOT / "papers" / value
            if not path.is_file():
                missing.append(f"{fig['id']}.{key}: {value}")
    assert not missing, f"F7/F9: declared paths missing: {missing}"


def test_no_pdfs_are_committed_under_papers() -> None:
    proc = subprocess.run(
        ["git", "ls-files", "papers/**/*.pdf"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = [line for line in proc.stdout.splitlines() if line.strip()]
    assert not tracked, f"F4: committed PDFs are forbidden: {tracked}"


def test_warehouse_tex_does_not_include_previews() -> None:
    tex = WAREHOUSE_TEX.read_text(encoding="utf-8")
    assert "previews/" not in tex


def test_warehouse_tex_keeps_figpreamble_and_allows_heatmap_pdfs() -> None:
    tex = WAREHOUSE_TEX.read_text(encoding="utf-8")
    assert r"\input{../figs/figpreamble.tex}" in tex
    assert r"\graphicspath{{./}}" not in tex
    assert "Figure3.pdf" not in tex
    assert "E1_repeat.pdf" in tex
    hits = [line.strip() for line in tex.splitlines() if PEERJ_INCLUDE.search(line)]
    assert not hits, f"F6: PeerJ FigureN.pdf includes: {hits}"


def test_warehouse_tex_is_full_canonical_not_a_stub() -> None:
    text = WAREHOUSE_TEX.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) >= 2000, f"F6b: stub manuscript ({len(lines)} lines)"
    assert "pointer-only" not in text.lower()
    assert r"\graphicspath{{./}}" not in text
    assert "figpreamble severed by build_submission_figs.py" not in text
    if CANONICAL_TEX is not None and CANONICAL_TEX.is_file():
        canonical = CANONICAL_TEX.read_text(encoding="utf-8")
        stripped = [
            line
            for line in canonical.splitlines()
            if line.strip() != r"\graphicspath{{./}}"
            and not line.strip().startswith("% figpreamble severed by build_submission_figs.py")
        ]
        assert abs(len(lines) - len(stripped)) <= max(5, int(0.05 * len(stripped))), (
            f"F6b: warehouse {len(lines)} vs canonical-stripped {len(stripped)}"
        )


def test_gitignore_excludes_compiled_figure_tiers() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "papers/figs/tex/" in gitignore or "figs/tex/" in gitignore
    assert "papers/figs/vec/" in gitignore or "figs/vec/" in gitignore
