"""GitHub Actions contract (I1–I3)."""

from __future__ import annotations

import yaml

from conftest import REPO_ROOT, workflow_path


def _load(name: str) -> dict:
    path = workflow_path(name)
    assert path.is_file(), f"missing .github/workflows/{name}"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_required_ci_workflow_exists() -> None:
    data = _load("ci.yml")
    jobs = data.get("jobs") or {}
    assert "required-contract-tests" in jobs or "contract" in jobs


def test_ci_runs_pytest_without_latex() -> None:
    data = _load("ci.yml")
    blob = yaml.safe_dump(data).lower()
    assert "pytest" in blob
    assert "latexmk" not in blob
    assert "pdflatex" not in blob


def test_pages_workflow_permissions_and_environment() -> None:
    data = _load("pages.yml")
    perms = data.get("permissions") or {}
    assert perms.get("pages") == "write"
    jobs = data.get("jobs") or {}
    env_names = []
    for job in jobs.values():
        env = job.get("environment")
        if isinstance(env, str):
            env_names.append(env)
        elif isinstance(env, dict):
            env_names.append(env.get("name"))
    assert "github-pages" in env_names


def test_pages_triggers_main_only_with_path_filter() -> None:
    data = _load("pages.yml")
    on = data.get("on") or data.get(True)
    assert isinstance(on, dict)
    assert "workflow_dispatch" in on
    push = on.get("push") or {}
    branches = push.get("branches") or []
    assert branches == ["main"] or branches == "main"
    paths = push.get("paths") or []
    joined = " ".join(paths)
    assert "portal/**" in joined
    assert "papers/FIGURE-INDEX.json" in joined
    pages_text = workflow_path("pages.yml").read_text(encoding="utf-8")
    assert "path: out" in pages_text
    assert "papers/figs/summaries/**" in joined
    assert "papers/figs/previews/**" in joined
    assert ".github/workflows/pages.yml" in joined
    assert "ci/comprehensive" not in yaml.safe_dump(data)


def test_no_workflow_runs_latexmk() -> None:
    workflows = list((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows
    for path in workflows:
        text = path.read_text(encoding="utf-8").lower()
        assert "latexmk" not in text
        assert "pdflatex" not in text
        assert "lualatex" not in text


def test_no_extra_visual_workflows_required() -> None:
    names = {p.name for p in (REPO_ROOT / ".github" / "workflows").glob("*.yml")}
    assert "visual-ralph.yml" not in names
    assert "visual-pixel.yml" not in names
