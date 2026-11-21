#!/usr/bin/env python3
"""Keep established master URLs current without deleting historical files."""
import os
import subprocess
from release_books import api


def read_tree(repo, sha):
    result = api(f"repos/{repo}/git/trees/{sha}?recursive=1")
    if result.get("truncated"):
        raise RuntimeError("Refusing an incomplete repository tree")
    return {entry["path"]: {key: entry[key] for key in ("path", "mode", "type", "sha")}
            for entry in result["tree"] if entry["type"] != "tree"}


def updates(source, previous):
    # Workflow files stay on their own branch; historical paths are never removed.
    return [entry for path, entry in source.items()
            if not path.startswith(".github/workflows/") and previous.get(path) != entry]


def sync(repo, sha):
    def current():
        return api(f"repos/{repo}/git/ref/heads/main")["object"]["sha"] == sha
    if not current():
        print("A newer main commit exists; compatibility update skipped.")
        return
    legacy = api(f"repos/{repo}/git/ref/heads/master")["object"]["sha"]
    source, previous = read_tree(repo, sha), read_tree(repo, legacy)
    changes = updates(source, previous)
    if not changes:
        print("Existing public URLs are already current.")
        return
    base = api(f"repos/{repo}/git/commits/{legacy}")["tree"]["sha"]
    tree = api(f"repos/{repo}/git/trees", "POST", {"base_tree": base, "tree": changes})
    expected = previous | {item["path"]: item for item in changes}
    assert read_tree(repo, tree["sha"]) == expected, "Compatibility tree changed an unexpected path"
    if not current():
        print("A newer main commit arrived; compatibility update skipped.")
        return
    commit = api(f"repos/{repo}/git/commits", "POST", {
        "message": f"Keep existing Wisdom URLs current (main@{sha[:12]})",
        "tree": tree["sha"], "parents": [legacy]})
    # A concurrent change to master makes this non-forced update fail visibly.
    api(f"repos/{repo}/git/refs/heads/master", "PATCH", {"sha": commit["sha"], "force": False})
    actual = api(f"repos/{repo}/git/ref/heads/master")["object"]["sha"]
    assert actual == commit["sha"], "Compatibility branch changed during verification"
    assert read_tree(repo, actual) == expected
    print(f"Preserved {len(previous)} existing paths; updated {len(changes)} current files.")


if __name__ == "__main__":
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    sync(os.environ.get("GITHUB_REPOSITORY", "merlinmann/wisdom"), sha)
