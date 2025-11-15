#! /usr/bin/env bash

# Ensure we are at the root of the project repository,
# regardless of where this script is run from.
cd "$(dirname "$0")/.."

# NOTES:
# Assumes we want exactly one wisdom per page in the EPUB.
# This assumes the md file is grouped into sections by h2 (##)
# and that within each section, each wisdom is a separate list item.

# Export EBOOK_VIEWER environment variable to specify the application
# Reasonable options: `calibre`, `Books`
EBOOK_VIEWER=${EBOOK_VIEWER:-"Books"}
# Append the current date to the EPUB filename
# DESTINATION="ebooks/Wisdom-$(date +%Y-%m-%d).epub"
DESTINATION="ebooks/wisdom.epub"

## Pass --debug to Pandoc for verbose output if needed.
if [[ "$1" == "--debug" ]]; then
  PANDOC_DEBUG="--verbose --log=ebooks/pandoc.log"
else
  PANDOC_DEBUG=""
fi

echo "Compiling wisdom.md to $DESTINATION..."
pandoc wisdom.md -o $DESTINATION \
  --metadata title="Merlin's Wisdom Project" \
  --metadata author="Merlin Mann" \
  --metadata date="$(date +%Y-%m-%d)" \
  --metadata description="Or: “Everybody likes being given a glass of water.”" \
  --metadata language="en" \
  --css=ebooks/style.css \
  --shift-heading-level-by=-1 \
  --toc --toc-depth=2 \
  --split-level=2 \
  --epub-cover-image=ebooks/cover.jpg \
  --lua-filter=ebooks/filters/strip-comments.lua \
  --lua-filter=ebooks/filters/process-md.lua \
  $PANDOC_DEBUG;

if [[ $? -ne 0 ]]; then
  echo "Error: pandoc failed to compile wisdom.md."
  exit 1
fi

## If debugging, expand the zip file to inspect its contents.
if [[ "$1" == "--debug" ]]; then
  echo "Debugging enabled. Compiled EPUB will be expanded for inspection."
  unzip -l $DESTINATION
  unzip -d ebooks/contents $DESTINATION
  echo "EPUB contents extracted to ebooks/contents/"
  exit 0
fi

## If the `open` command is available, open the EPUB after compiling.
if command -v open &> /dev/null; then
  echo "Opening $DESTINATION..."
  open $DESTINATION -a $EBOOK_VIEWER
else
  echo "Compiled successfully. You can find the EPUB at ebooks/wisdom.epub"
fi

exit 0
