#!/usr/bin/env python3
"""Check source preservation and render evidence from the actual ebook files."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import unicodedata
import zipfile
from xml.etree import ElementTree as ET


def canonical(text):
    return ''.join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.units = []
        self.active = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("p", "li", "h1", "h2") or (tag == "div" and attrs.get("class") == "csl-entry"):
            self.active.append([tag, []])

    def handle_endtag(self, tag):
        if self.active and self.active[-1][0] == tag:
            self.units.append(''.join(self.active.pop()[1]))

    def handle_data(self, value):
        self.text.append(value)
        for _, parts in self.active:
            parts.append(value)


def validate(folder):
    import pymupdf
    from PIL import Image, ImageDraw
    support = folder / "Supporting files"
    source = Text()
    source.feed((support / "source.html").read_text())
    units = [canonical(x) for x in source.units if len(canonical(x)) > 3]
    with zipfile.ZipFile(folder / "wisdom.epub") as archive:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        opf_path = next(container.iter("{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")).attrib["full-path"]
        opf = ET.fromstring(archive.read(opf_path))
        ns = {"o": "http://www.idpf.org/2007/opf"}
        items = {x.attrib["id"]: x.attrib["href"] for x in opf.findall("o:manifest/o:item", ns)}
        spine = [items[x.attrib["idref"]] for x in opf.findall("o:spine/o:itemref", ns)]
        epub_text = []
        chapter = None
        longest = 0
        for item in spine:
            path = str(Path(opf_path).parent / item)
            body = archive.read(path).decode()
            reader = Text()
            reader.feed(body)
            epub_text.extend(reader.text)
            if len("".join(reader.text)) > longest:
                chapter, longest = path, len("".join(reader.text))
        epub = canonical(' '.join(epub_text))
        missing = [unit for unit in units if unit not in epub]
        assert not missing, f"EPUB omitted {len(missing)} source passages: {missing[:2]}"
        preview = support / "epub-preview"
        for item in archive.infolist():
            assert not Path(item.filename).is_absolute() and '..' not in Path(item.filename).parts
        archive.extractall(preview)
        assert chapter
        (support / "epub-preview-path.txt").write_text(str((preview / chapter).resolve()))

    doc = pymupdf.open(folder / "wisdom.pdf")
    pages = []
    clipped = []
    for number, page in enumerate(doc):
        # Exclude running headers and folios before comparing paragraph content.
        pages.append(page.get_text(clip=pymupdf.Rect(0, 39, page.rect.width, page.rect.height - 38)))
        for word in page.get_text("words"):
            if word[0] < -1 or word[1] < -1 or word[2] > page.rect.width + 1 or word[3] > page.rect.height + 1:
                clipped.append(number + 1)
    pdf = canonical(' '.join(pages))
    missing = [unit for unit in units if unit not in pdf]
    assert not missing, f"PDF omitted {len(missing)} source passages: {missing[:3]}"
    assert not clipped, f"Text outside page bounds: {clipped}"
    empty_pages = [n + 1 for n, text in enumerate(pages) if n > 0 and len(text.strip()) <= 12 and not doc[n].get_image_info()]
    assert doc.get_toc(), "PDF bookmarks are missing"

    renders = support / "rendered"
    renders.mkdir(exist_ok=True)
    thumbs = []
    for number, page in enumerate(doc):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(.55, .55), alpha=False)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        thumbs.append(image)
    for batch in range(0, len(thumbs), 12):
        tile_w, tile_h = thumbs[0].width + 16, thumbs[0].height + 28
        sheet = Image.new("RGB", (tile_w * 4, tile_h * 3), "#d9d5cf")
        draw = ImageDraw.Draw(sheet)
        for offset, thumb in enumerate(thumbs[batch:batch+12]):
            x, y = offset % 4 * tile_w + 8, offset // 4 * tile_h + 20
            sheet.paste(thumb, (x, y))
            draw.text((x, y - 16), str(batch + offset + 1), fill="black")
        sheet.save(renders / f"overview-{batch//12+1}.png")
    selected = sorted({0, 1, 2, 3, 4, 5, 8, len(doc)//2, len(doc)-2, len(doc)-1} & set(range(len(doc))))
    for number in selected:
        doc[number].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False).save(renders / f"page-{number+1:03}.png")
    report = {"source_passages_checked": len(units), "epub_content_preserved": True,
              "pdf_content_preserved": True, "pdf_pages": len(doc), "pdf_bookmarks": len(doc.get_toc()),
              "empty_pages": empty_pages, "text_outside_pages": clipped, "pdf_fonts": sorted({font[3] for page in doc for font in page.get_fonts()})}
    (support / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    assert not empty_pages, f"Unexpected empty pages: {empty_pages}"
    assert any("sourceserif" in canonical(name) for name in report["pdf_fonts"]), "The book font was not embedded"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=Path, default=Path("builds/ebooks"))
    validate(parser.parse_args().folder)
