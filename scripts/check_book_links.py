#!/usr/bin/env python3
"""Validate published Markdown paths and anchors using Pandoc's parsed links."""
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def check():
    tracked = set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines())
    tracked = {name for name in tracked if (ROOT / name).is_file()}
    links, anchors = [], {}

    class HTMLLinks(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if attrs.get("id"): anchors[file].add(attrs["id"])
            key = "href" if tag == "a" else "src" if tag == "img" else None
            if key and attrs.get(key): links.append((file, attrs[key]))

    for file in sorted(name for name in tracked if name.endswith(".md")):
        anchors[file] = set()
        parser = HTMLLinks()
        ast = json.loads(subprocess.check_output(
            ["pandoc", "-f", "gfm-yaml_metadata_block", "-t", "json", file], cwd=ROOT, text=True))
        def walk(item):
            if isinstance(item, dict):
                kind = item.get("t")
                if kind in ("Link", "Image"): links.append((file, item["c"][-1][0]))
                if kind == "Header": anchors[file].add(item["c"][1][0])
                if kind in ("RawInline", "RawBlock") and item["c"][0] == "html": parser.feed(item["c"][1])
                for child in item.values(): walk(child)
            elif isinstance(item, list):
                for child in item: walk(child)
        walk(ast)
    failures = []
    for file, link in links:
        url = urlsplit(link)
        if url.scheme or url.netloc: continue
        path = unquote(url.path)
        target = ((path.lstrip("/") if path.startswith("/") else posixpath.normpath(posixpath.join(posixpath.dirname(file), path))) if path else file)
        if target not in tracked:
            failures.append({"file": file, "url": link, "error": "missing file"})
        elif url.fragment and unquote(url.fragment) not in anchors.get(target, set()):
            failures.append({"file": file, "url": link, "error": "missing anchor"})
    report = {"markdown_files": len(anchors), "links": len(links), "failures": failures,
              "external_urls": sorted({url for _, url in links if url.startswith("http")})}
    output = ROOT / "builds/ebooks/Supporting files/link-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if failures: raise SystemExit(1)


if __name__ == "__main__":
    check()
