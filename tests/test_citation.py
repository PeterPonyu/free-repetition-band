"""Citation / DOI hygiene (C1, C3, C4)."""

from pathlib import Path

import yaml


def _cff(repo_root: Path) -> dict:
    path = repo_root / "CITATION.cff"
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_citation_cff_parses_as_mapping(repo_root: Path) -> None:
    cff = _cff(repo_root)
    assert "title" in cff
    assert isinstance(cff["title"], str)


def test_citation_cff_doi_is_manuscript_concept(repo_root: Path) -> None:
    cff = _cff(repo_root)
    assert cff.get("doi") == "10.5281/zenodo.21020378"


def test_citation_cff_lists_version_doi_under_identifiers(repo_root: Path) -> None:
    cff = _cff(repo_root)
    identifiers = cff.get("identifiers") or []
    values = {item.get("value") for item in identifiers if isinstance(item, dict)}
    assert "10.5281/zenodo.21020379" in values


def test_citation_cff_is_not_five_paper_bundle(repo_root: Path) -> None:
    text = (repo_root / "CITATION.cff").read_text(encoding="utf-8")
    assert "muon-norm-cap-grokking" not in text
    assert "calibration-traps" not in text
    assert "architecture-staircase" not in text
