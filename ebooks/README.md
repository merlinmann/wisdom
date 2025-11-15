# wisdom.epub

This is the latest version of the document exported from .md via Pandoc.

To compile this ebook, run the following command in the terminal:

```bash
./ebooks/compile.sh
```

The script assumes you have Pandoc installed. On macOS, you can install it using Homebrew:

```bash
brew install pandoc
```

## Markdown Pre-Processing

We use Pandoc's lua filters to process the Markdown files before converting them to EPUB.

You can add as many filters as you like in the `ebooks/filters` directory. The filters will be applied in the order they are listed in the `compile.sh` script.

ChatGPT and Claude are pretty good at drafting lua filters.
