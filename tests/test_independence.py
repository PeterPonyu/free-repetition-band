"""Independence / freeze hygiene that applies to this warehouse (Z3, U5)."""

from pathlib import Path


def test_portal_does_not_present_a_five_paper_suite(repo_root: Path) -> None:
    portal = repo_root / "portal"
    html = (portal / "index.html").read_text(encoding="utf-8")
    for foreign in (
        "muon-norm-cap-grokking",
        "grokking-clock",
        "architecture-staircase",
        "calibration-traps",
    ):
        assert foreign not in html


def test_readme_does_not_link_a_shared_five_paper_site(repo_root: Path) -> None:
    text = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "peterponyu.github.io/muon-norm-cap-grokking" not in text.lower()
    assert "paper-a" not in text.lower()
