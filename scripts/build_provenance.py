"""Identify the producing execution without changing reproducible book bytes."""
import os
import re
from urllib.parse import urlsplit


def _positive(value):
    if isinstance(value, bool) or not re.fullmatch(r"[1-9][0-9]*", str(value)):
        raise ValueError("Build identifiers must be positive integers")
    return int(value)


def validate_build_identity(build):
    if not isinstance(build, dict):
        raise ValueError("Missing build identity")
    if build.get("provider") == "local" and set(build) == {"provider"}:
        return
    if build.get("provider") != "github-actions":
        raise ValueError("Unknown build provider")
    repo = build.get("repository", "")
    if not isinstance(repo, str) or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        raise ValueError("Invalid build repository")
    for key in ("run_id", "run_number", "run_attempt"):
        _positive(build.get(key))
    if not isinstance(build["run_id"], str) or any(type(build[k]) is not int for k in ("run_number", "run_attempt")):
        raise ValueError("Expected a string run ID and integer run number and attempt")
    if not re.fullmatch(re.escape(repo) + r"/\.github/workflows/[^/@\s]+\.ya?ml@refs/[^\s]+", build.get("workflow_ref", "")):
        raise ValueError("Invalid build workflow reference")
    if not re.fullmatch(r"[0-9a-f]{40}", build.get("workflow_commit", "")):
        raise ValueError("Invalid build workflow commit")
    url = urlsplit(build.get("url", ""))
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment or url.path != f"/{repo}/actions/runs/{build['run_id']}"):
        raise ValueError("Invalid build run URL")


def build_identity(source_commit, environ=None):
    """Capture CI identity in the build job; local conversions have no CI number."""
    env = os.environ if environ is None else environ
    if env.get("GITHUB_ACTIONS") != "true":
        return {"provider": "local"}
    if env.get("GITHUB_SHA") != source_commit:
        raise ValueError("Build source does not match the GitHub Actions revision")
    build = {
        "provider": "github-actions",
        "repository": env.get("GITHUB_REPOSITORY", ""),
        "run_id": env.get("GITHUB_RUN_ID", ""),
        "run_number": _positive(env.get("GITHUB_RUN_NUMBER")),
        "run_attempt": _positive(env.get("GITHUB_RUN_ATTEMPT")),
        "workflow_ref": env.get("GITHUB_WORKFLOW_REF", ""),
        "workflow_commit": env.get("GITHUB_WORKFLOW_SHA", ""),
    }
    build["url"] = f"{env.get('GITHUB_SERVER_URL', '')}/{build['repository']}/actions/runs/{build['run_id']}"
    validate_build_identity(build)
    return build


def publication_build(build, repo, source_commit, environ=None):
    """A publish-only retry may consume an earlier producing attempt, unchanged."""
    validate_build_identity(build)
    current = build_identity(source_commit, environ)
    if build.get("provider") != "github-actions" or current.get("provider") != "github-actions":
        raise ValueError("Publication requires a GitHub Actions build")
    if build["repository"] != repo:
        raise ValueError("Build belongs to another repository")
    for key in ("repository", "run_id", "run_number", "workflow_ref", "workflow_commit", "url"):
        if build[key] != current[key]:
            raise ValueError(f"Build does not belong to this publishing workflow: {key}")
    if build["run_attempt"] > current["run_attempt"]:
        raise ValueError("Build attempt is newer than the publishing attempt")
    label = f"Build {build['run_number']} (attempt {build['run_attempt']})"
    return f"[{label}]({build['url']}/attempts/{build['run_attempt']})"
