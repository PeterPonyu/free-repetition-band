"""Workflow contract: required CI vs gated Pages / visual-pixel (I2, I3)."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_workflow(repo_root: Path, name: str) -> dict:
    path = repo_root / ".github" / "workflows" / name
    assert path.is_file(), f".github/workflows/{name} must exist"
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _workflow_text(repo_root: Path, name: str) -> str:
    return (repo_root / ".github" / "workflows" / name).read_text(encoding="utf-8")


def test_pages_workflow_declares_pages_write_permission(repo_root: Path) -> None:
    wf = _load_workflow(repo_root, "pages.yml")
    perms = wf.get("permissions") or {}
    assert perms.get("pages") == "write"
    assert perms.get("id-token") == "write"


def test_pages_workflow_declares_github_pages_environment(repo_root: Path) -> None:
    text = _workflow_text(repo_root, "pages.yml")
    assert "github-pages" in text


def test_pages_workflow_path_filters_are_portal_and_paper_contracts_only(
    repo_root: Path,
) -> None:
    wf = _load_workflow(repo_root, "pages.yml")
    # PyYAML 1.1 treats the GitHub Actions key `on:` as boolean True.
    on_block = wf.get("on") or wf.get(True) or {}
    push = on_block.get("push") or {}
    paths = push.get("paths") or []
    assert "portal/**" in paths
    assert "paper/FIGURE-INDEX.json" in paths
    assert "paper/summaries/**" in paths
    assert "paper/previews/**" in paths
    assert "experiments/**" not in paths


def test_pages_deploy_job_is_gated_so_pages_is_not_enabled(repo_root: Path) -> None:
    wf = _load_workflow(repo_root, "pages.yml")
    jobs = wf.get("jobs") or {}
    assert "deploy" in jobs
    deploy_if = str(jobs["deploy"].get("if", "")).lower().replace(" ", "")
    assert deploy_if in {"false", "${{false}}"}


def test_required_ci_workflow_runs_pytest(repo_root: Path) -> None:
    text = _workflow_text(repo_root, "ci.yml")
    assert "pytest" in text
    assert "latexmk" not in text


def test_required_ci_workflow_does_not_deploy_pages(repo_root: Path) -> None:
    text = _workflow_text(repo_root, "ci.yml")
    assert "deploy-pages" not in text
    assert "upload-pages-artifact" not in text


def test_visual_pixel_workflow_is_gated_until_reference_approved(
    repo_root: Path,
) -> None:
    wf = _load_workflow(repo_root, "visual-pixel.yml")
    jobs = wf.get("jobs") or {}
    assert jobs, "visual-pixel.yml must define a job"
    for name, job in jobs.items():
        raw_if = str(job.get("if", "")).lower().replace(" ", "")
        assert raw_if in {"false", "${{false}}"}, (
            f"visual-pixel job {name!r} must be gated with if: false until "
            "reference.png is user-approved"
        )


def test_no_workflow_runs_latexmk_or_uploads_figure_pdfs(repo_root: Path) -> None:
    workflows = repo_root / ".github" / "workflows"
    assert workflows.is_dir()
    for path in workflows.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        assert "latexmk" not in text
        assert "pdflatex" not in text
