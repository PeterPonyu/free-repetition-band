"""Figure-pointer contract (test-spec F1–F8) for Paper E1."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import jsonschema

MANIFEST_IDS = frozenset(
    {
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
)
SCHEMATIC_IDS = frozenset({"E1_landscape", "E1_scheme"})
ALLOWED_IDS = MANIFEST_IDS | SCHEMATIC_IDS


def _index(repo_root: Path) -> dict:
    path = repo_root / "paper" / "FIGURE-INDEX.json"
    assert path.is_file(), "paper/FIGURE-INDEX.json must exist"
    return json.loads(path.read_text(encoding="utf-8"))


def test_figure_index_validates_against_schema(repo_root: Path) -> None:
    schema = json.loads(
        (repo_root / "tests" / "schemas" / "figure-index.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.validate(instance=_index(repo_root), schema=schema)


def test_every_index_id_is_manifest_or_documented_schematic(repo_root: Path) -> None:
    ids = {fig["id"] for fig in _index(repo_root)["figures"]}
    unexpected = ids - ALLOWED_IDS
    assert not unexpected, f"undeclared figure ids: {sorted(unexpected)}"


def test_index_includes_every_manifest_artifact(repo_root: Path) -> None:
    ids = {fig["id"] for fig in _index(repo_root)["figures"]}
    missing = MANIFEST_IDS - ids
    assert not missing, f"manifest artifacts missing from INDEX: {sorted(missing)}"


def test_git_lists_no_pdf_under_paper_tree(repo_root: Path) -> None:
    listed = subprocess.check_output(
        ["git", "ls-files", "paper/**/*.pdf", "papers/**/*.pdf"],
        cwd=repo_root,
        text=True,
    ).strip()
    assert listed == "", f"committed PDFs in paper tree:\n{listed}"


def test_working_tree_has_no_pdf_beside_pointer_tex(repo_root: Path) -> None:
    paper = repo_root / "paper"
    pdfs = sorted(paper.rglob("*.pdf")) if paper.is_dir() else []
    assert pdfs == [], f"untracked/working PDFs under paper/: {pdfs}"


def test_pointer_tex_does_not_mention_previews(repo_root: Path) -> None:
    tex = repo_root / "paper" / "main.tex"
    assert tex.is_file(), "paper/main.tex must exist"
    text = tex.read_text(encoding="utf-8")
    assert "previews/" not in text


def test_pointer_tex_does_not_include_peerj_figure_pdfs(repo_root: Path) -> None:
    tex = (repo_root / "paper" / "main.tex").read_text(encoding="utf-8")
    assert re.search(r"Figure\d+\.pdf", tex) is None


def test_pointer_tex_uses_figtikz_or_preamble_routed_names(repo_root: Path) -> None:
    tex = (repo_root / "paper" / "main.tex").read_text(encoding="utf-8")
    uses_figtikz = r"\figtikz{" in tex
    uses_preamble = "figpreamble" in tex
    assert uses_figtikz or uses_preamble


def test_pointer_tex_does_not_includegraphics_same_directory_pdf(repo_root: Path) -> None:
    tex = (repo_root / "paper" / "main.tex").read_text(encoding="utf-8")
    for match in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex):
        name = match.group(1)
        assert "/" in name or name.startswith("{"), (
            f"same-directory includegraphics is forbidden: {name}"
        )
        assert not name.endswith(".pdf") or "figs/vec" in name or "vec/" in name


def test_every_manifest_summary_json_is_committed(repo_root: Path) -> None:
    index = _index(repo_root)
    missing = []
    for fig in index["figures"]:
        summary = fig.get("summary")
        if not summary:
            continue
        path = repo_root / "paper" / summary
        if not path.is_file():
            missing.append(str(path.relative_to(repo_root)))
    assert missing == [], f"missing summaries: {missing}"


def test_gitignore_excludes_compiled_tex_and_vec_tiers(repo_root: Path) -> None:
    text = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert "figs/tex/" in text
    assert "figs/vec/" in text
