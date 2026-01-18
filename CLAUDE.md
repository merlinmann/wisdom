# Merlin's Wisdom Project

A collection of advice and observations. "It's only advice for you because it had to be advice for me."

Website: http://wisdom.limo

## Structure
- `wisdom.md` - Main content (the wisdom itself)
- `3d.md` - Observations from 3D printing
- `quotes.md` - Collected quotes
- `inspirado.md` - Inspiration/misc
- `i/` - Images referenced in content
- `ebooks/` - EPUB output and cover image

## Building the EPUB

The markdown uses absolute image paths (`/i/`) that need fixing for Pandoc:

```bash
sed 's|(/i/|(i/|g' wisdom.md | pandoc \
  --to=epub3 \
  --output=ebooks/wisdom-$(date +%s).epub \
  --epub-cover-image=ebooks/cover.jpg \
  --metadata title="Merlin's Wisdom Project" \
  --metadata author="Merlin Mann" \
  --metadata lang="en-US" \
  --toc
```

## Notes
- Cover image: `ebooks/cover.jpg`
- Author photos in `i/` (MANN-angry variants, my-cover variants)
- The `mmd-style-demo/` folder has PDF/citation tooling (separate from EPUB workflow)
