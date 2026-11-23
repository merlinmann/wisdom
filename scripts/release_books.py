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
VERSION = re.compile(r"^v20\d{2}\.(?:[1-9]\d*|(?:[1-9]|1[0-2])\.[1-9]\d*)$")
MONTHLY_VERSION = re.compile(r"^v(20\d{2})\.([1-9]|1[0-2])\.([1-9]\d*)$")


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


def book_inputs(repo, sha):
    """Compare source bytes, including deletions, without rebuilding the books."""
    tree = api(f"repos/{repo}/git/trees/{sha}?recursive=1")
    if tree.get("truncated"):
        raise RuntimeError("Cannot compare an incomplete book input tree")
    records = []
    for item in tree["tree"]:
        path = item["path"]
        if path in ("book/README.md", "book/data-formats.md", "scripts/check_book_links.py", "scripts/sync_legacy.py") or path.startswith("scripts/test_"):
            continue
        if item["type"] != "tree" and (path in ("wisdom.md", ".github/workflows/books.yml")
                or path.startswith(("i/", "book/", "scripts/"))):
            records.append((path, item["mode"], item["type"], item["sha"]))
    if not any(row[0] == "wisdom.md" for row in records):
        raise RuntimeError("Cannot compare book inputs without the manuscript")
    return hashlib.sha256(json.dumps(sorted(records)).encode()).hexdigest()


def latest_publication(items):
    """Publication order survives the switch from legacy year.sequence tags."""
    published = [item for item in items if not item["draft"]
                 and not item.get("prerelease", False) and VERSION.fullmatch(item["tag_name"])]
    return max(published, key=lambda item: item["published_at"], default=None)


def unchanged_since_publication(repo, sha, items):
    latest = latest_publication(items)
    if latest is None:
        return False
    source = latest["target_commitish"]
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise RuntimeError("Published edition must identify an immutable source commit")
    return book_inputs(repo, sha) == book_inputs(repo, source)


def resume_schedule(repo):
    """Resume an inactivity-disabled schedule after new checked work arrives."""
    workflow = f"repos/{repo}/actions/workflows/books.yml"
    state = api(workflow)["state"]
    if state == "disabled_inactivity":
        gh("api", workflow + "/enable", "--method", "PUT")
        assert api(workflow)["state"] == "active", "Book schedule did not resume"
        print("Resumed the daily book schedule after repository inactivity.")
    else:
        print(f"Book schedule is {state}; its setting was preserved.")


def choose_version(items, tags, sha, day):
    for item in items:
        if item["target_commitish"] == sha and VERSION.fullmatch(item["tag_name"]):
            return item["tag_name"][1:], not item["draft"]
    taken = [int(match[3]) for tag in tags if (match := MONTHLY_VERSION.fullmatch(tag))
             and (int(match[1]), int(match[2])) == (day.year, day.month)]
    sequence = max(taken, default=0) + 1
    return f"{day.year}.{day.month}.{sequence}", False


def plan(repo, path, verify_only=False):
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    day = datetime.now(timezone.utc).astimezone(ZoneInfo("America/Los_Angeles")).date()
    items = releases(repo)
    pages = json.loads(gh("api", f"repos/{repo}/tags?per_page=100", "--paginate", "--slurp"))
    tags = [x["name"] for page in pages for x in page] + [x["tag_name"] for x in items]
    version, exists = choose_version(items, tags, sha, day)
    unchanged = not exists and unchanged_since_publication(repo, sha, items)
    build = verify_only or not (exists or unchanged)
    result = {"version": version, "sha": sha, "already_published": exists,
              "unchanged_inputs": unchanged, "build": build,
              "verify_only": verify_only, "repository": repo}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"version={version}\nbuild={'true' if build else 'false'}\n")
    print(json.dumps(result))


def publish(repo, folder):
    proposal = json.loads((folder / "Supporting files/release-plan.json").read_text())
    assert not proposal.get("verify_only", False), "A review-only build must never be published"
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
    prior = latest_publication(items)
    compare = f"https://github.com/{repo}/compare/{prior['tag_name']}...{tag}" if prior else f"https://github.com/{repo}/commit/{sha}"
    correction = ""
    if version == "2026.11.1":
        correction = "Merlin and Codex both goofed the release numbering while trying to borrow Marco’s system. We got a little ahead of the calendar. We’re starting over at **2026.11.1**: year, month, edition within that month. Next comes **2026.11.2**, and December starts at **2026.12.1**. Earlier downloads keep their original names and links.\n\n"
    notes = f'''## Merlin’s Wisdom Project — {version}

{correction}- **EPUB:** adjustable text for e-readers and reading apps; Kindle readers can use [Send to Kindle](https://www.amazon.com/sendtokindle).
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
    parser.add_argument("action", choices=["plan", "publish", "resume-schedule"])
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "merlinmann/wisdom"))
    parser.add_argument("--folder", type=Path, default=Path("builds/ebooks"))
    parser.add_argument("--verify-only", action="store_true", help="build review copies even if unchanged; forbid publication")
    args = parser.parse_args()
    if args.verify_only and args.action != "plan":
        parser.error("--verify-only applies only to planning a review build")
    if args.action == "plan":
        plan(args.repo, args.folder / "Supporting files/release-plan.json", args.verify_only)
    elif args.action == "publish":
        publish(args.repo, args.folder)
    else:
        resume_schedule(args.repo)
