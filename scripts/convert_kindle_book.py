"""Run inside the pinned Calibre runtime, with stable IDs and publication time."""
import hashlib
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


def main():
    source, destination, epoch = sys.argv[1:]
    epoch = int(epoch)
    # Calibre's Palm database headers use time.time() and random IDs. Its metadata
    # can also synthesize UUIDs and dates. Scope stable values to this conversion
    # process so an identical edition rebuilds byte for byte.
    seed = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    random.seed(seed)
    uuid.uuid4 = lambda: uuid.UUID(int=random.getrandbits(128), version=4)
    time.time = lambda: epoch
    import calibre.utils.date
    calibre.utils.date.now = lambda: datetime.fromtimestamp(epoch, timezone.utc)
    calibre.utils.date.utcnow = lambda: datetime.fromtimestamp(epoch, timezone.utc)
    from calibre.ebooks.conversion.cli import main as convert
    preview = Path(destination).parent / "Supporting files/kindle-preview"
    sys.argv = ["ebook-convert", source, destination, "--output-profile", "kindle_pw3",
                "--no-inline-toc", "--disable-font-rescaling", "--chapter", "/",
                "--page-breaks-before", "/", "--extract-to", str(preview)]
    return convert(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
