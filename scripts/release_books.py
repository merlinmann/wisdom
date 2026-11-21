#!/usr/bin/env python3
"""Plan and publish complete, versioned editions through GitHub CLI."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

ASSETS = ("wisdom.epub", "wisdom.pdf", "wisdom.html", "wisdom.azw3", "wisdom.md", "wisdom.json", "wisdom.sqlite", "edition.json", "SHA256SUMS")
VERSION = re.compile(r"^v(20\d{2})\.([1-9]\d*)$")


def gh(*args, **kwargs):
    return subprocess.check_output(["gh", *args], text=True, **kwargs)


def api(path, method="GET", payload=None):
    args = ["api", path, "--method", method]
    if payload is not None:
        args += ["--input", "-"]
    return json.loads(gh(*args, input=json.dumps(payload) if payload is not None else None))


def releases(repo):
    pages = json.loads(gh("api", f"repos/{repo}/releases?per_page=100", "--paginate", "--slurp"))
    return [item for page in pages for item in page]


def choose_version(items, tags, sha, day):
    for item in items:
        if item["target_commitish"] == sha and VERSION.fullmatch(item["tag_name"]):
            return item["tag_name"][1:], not item["draft"]
    taken = [int(match[2]) for tag in tags if (match := VERSION.fullmatch(tag)) and int(match[1]) == day.year]
    sequence = max(day.month, max(taken, default=0) + 1)
    return f"{day.year}.{sequence}", False


def plan(repo, path):
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    epoch = int(subprocess.check_output(["git", "show", "-s", "--format=%ct", "HEAD"], text=True))
    day = datetime.fromtimestamp(epoch, timezone.utc).astimezone(ZoneInfo("America/Los_Angeles")).date()
    items = releases(repo)
    pages = json.loads(gh("api", f"repos/{repo}/tags?per_page=100", "--paginate", "--slurp"))
    tags = [x["name"] for page in pages for x in page] + [x["tag_name"] for x in items]
    version, exists = choose_version(items, tags, sha, day)
    result = {"version": version, "sha": sha, "already_published": exists, "repository": repo}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"version={version}\nbuild={'false' if exists else 'true'}\n")
    print(json.dumps(result))


def publish(repo, folder):
    proposal = json.loads((folder / "Supporting files/release-plan.json").read_text())
    manifest = json.loads((folder / "edition.json").read_text())
    sha, version = proposal["sha"], proposal["version"]
    assert manifest["source_commit"] == sha and manifest["version"] == version
    tag = "v" + version
    head = api(f"repos/{repo}/branches/main")["commit"]["sha"]
    if head != sha:
        print("A newer source commit exists; this build will not replace the current edition.")
        return
    items = releases(repo)
    existing = next((x for x in items if x["tag_name"] == tag), None)
    if existing and not existing["draft"]:
        assert existing["target_commitish"] == sha, "Published version belongs to another source commit"
        print("This edition is already published; no files were changed.")
        return
    if existing:
        assert existing["target_commitish"] == sha, "Draft version belongs to another source commit"
    for name in ASSETS:
        assert (folder / name).is_file() and (folder / name).stat().st_size > 0, name
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert name in ASSETS and hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
    prior = next((x for x in items if not x["draft"] and VERSION.fullmatch(x["tag_name"])), None)
    compare = f"https://github.com/{repo}/compare/{prior['tag_name']}...{tag}" if prior else f"https://github.com/{repo}/commit/{sha}"
    notes = f'''## Merlin’s Wisdom Project — {version}

- **EPUB:** adjustable text for e-readers and reading apps; Kindle readers can use [Send to Kindle](https://www.amazon.com/sendtokindle).
- **PDF:** a typeset edition with fixed pages.
- **HTML:** a complete offline edition with its images and fonts included.
- **AZW3:** a Kindle edition for USB transfer or Calibre. For Amazon’s Send to Kindle service, use the EPUB.
- **Markdown:** image-free text with headings, emphasis, links, and YAML edition metadata.
- **JSON:** ordered sections and entries with text, Markdown, citations, links, and edition metadata.
- **SQLite:** the same structured data in one portable database, with full-text search.

All seven formats preserve the manuscript text and identify this edition and its exact source commit. Data-record IDs are specific to this edition; permanent cross-edition IDs remain a separate design decision.

[Changes in this edition]({compare}) · [Source commit](https://github.com/{repo}/commit/{sha})

`SHA256SUMS` verifies the downloads. `edition.json` records the source and build tools. GitHub’s artifact attestations establish the provenance of all seven formats.
'''
    if existing is None:
        existing = api(f"repos/{repo}/releases", "POST", {"tag_name": tag, "target_commitish": sha, "name": f"Wisdom — {version}", "body": notes, "draft": True, "prerelease": False})
    gh("release", "upload", tag, *[str(folder / name) for name in ASSETS], "--repo", repo, "--clobber")
    verify = folder / "Supporting files/published-assets"
    verify.mkdir(exist_ok=True)
    gh("release", "download", tag, "--repo", repo, "--dir", str(verify), "--clobber")
    for name in ASSETS:
        assert (verify / name).read_bytes() == (folder / name).read_bytes(), f"Uploaded asset differs: {name}"
    current = api(f"repos/{repo}/branches/main")["commit"]["sha"]
    if current != sha:
        print("A newer commit arrived during upload; the verified draft remains unpublished.")
        return
    # Tag creation and publication use the explicit source SHA; no moving branch is used.
    refs = api(f"repos/{repo}/git/matching-refs/tags/{tag}")
    exact = next((x for x in refs if x["ref"] == f"refs/tags/{tag}"), None)
    if exact:
        assert exact["object"]["type"] == "commit" and exact["object"]["sha"] == sha
    else:
        api(f"repos/{repo}/git/refs", "POST", {"ref": f"refs/tags/{tag}", "sha": sha})
    gh("release", "edit", tag, "--repo", repo, "--draft=false", "--latest")
    result = api(f"repos/{repo}/releases/tags/{tag}")
    assert not result["draft"] and {x["name"] for x in result["assets"]} == set(ASSETS)
    assert api(f"repos/{repo}/releases/latest")["tag_name"] == tag
    print(result["html_url"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["plan", "publish"])
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "merlinmann/wisdom"))
    parser.add_argument("--folder", type=Path, default=Path("builds/ebooks"))
    args = parser.parse_args()
    if args.action == "plan":
        plan(args.repo, args.folder / "Supporting files/release-plan.json")
    else:
        publish(args.repo, args.folder)
