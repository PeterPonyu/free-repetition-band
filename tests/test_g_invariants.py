"""G4 dual-license notice (MIT code / CC BY 4.0 data+figures)."""

from pathlib import Path


def test_license_states_mit_for_source_code(repo_root: Path) -> None:
    text = (repo_root / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "SOURCE CODE" in text


def test_license_states_cc_by_40_for_data_and_figures(repo_root: Path) -> None:
    text = (repo_root / "LICENSE").read_text(encoding="utf-8")
    assert "CC BY 4.0" in text or "Creative Commons Attribution 4.0" in text
    assert "DATA artifacts" in text or "data" in text.lower()
