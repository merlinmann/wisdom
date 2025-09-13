# Pandoc → Zotero → XeLaTeX → MLA 9
*A complete, reproducible workflow with fonts, styles, and troubleshooting.*

This document shows how to:

- collect/verify book data in Zotero (MLA-ish),
- export a stable `.bib` (Better BibTeX),
- wire Pandoc + citeproc + MLA CSL,
- produce a clean **Works Cited**,
- use **Equity** as the text face (with macOS fallbacks),
- diagnose common Pandoc/LaTeX failures quickly.

Everything below lives in **one file** (this one). Code and examples are fenced where appropriate; all prose is part of this same document.

---

## 1) Requirements (install + verify)

- **Pandoc** — <https://pandoc.org/>
- **MacTeX** (gives you **XeLaTeX**) — <https://tug.org/mactex/>
- **Zotero** + **Better BibTeX** — <https://retorque.re/zotero-better-bibtex/>
- **MLA CSL** — save the style as `mla.csl` (from the CSL repo)
- **Plain-text editor** (e.g., BBEdit)

Verify XeLaTeX is available:

```sh
which xelatex
xelatex --version
```

Expected path on macOS: `/Library/TeX/texbin/xelatex`.

> If `which xelatex` prints nothing, add TeX to PATH:
>
> ```sh
> echo 'export PATH="/Library/TeX/texbin:$PATH"' >> ~/.zprofile
> exec zsh
> ```

---

## 2) Export bibliography from Zotero (keys you control)

1. In Zotero select the items you want.
2. **Export** → **Better BibTeX (.bib)**.
3. Save as `references.bib` in your project folder.

You’ll get stable keys like:

```bibtex
@book{boylesModernMansGuide1987,
  title     = {The Modern Man's Guide to Life},
  author    = {Boyles, Denis and Rose, Alan and Wellikoff, Alan},
  publisher = {Harper \& Row},
  year      = {1987}
}
```

**Key management tips**

- In Zotero, set Better BibTeX to **pin** citation keys so they don’t change.
- If you fix a title/author, re-export the `.bib`.
- Ampersands in BibTeX publishers should be written `\&`.

---

## 3) MLA style (CSL) & sorting behavior

- Use the **Modern Language Association 9th edition (in-text citations)** CSL.
- MLA sorts the Works Cited **alphabetically by author (surname)**.
- Multiple works by the same author are sorted by **title**; in print MLA, the author name is replaced by a three-em dash after the first entry. (Pandoc/CSL often repeats the name; acceptable for most workflows.)
- Cite **the version you used**. If helpful, you can add original publication info in notes, but MLA’s default is the edition in hand.

---

## 4) Project layout

```
your-project/
├── demo.md
├── references.bib
└── mla.csl
```

Everything below assumes you’re in `your-project/`.

---

## 5) The Markdown source you can actually build

Paste this at the top of **`demo.md`** (YAML must start at line 1, col 1; save as UTF-8 **without BOM**):

```markdown
---
title: Demo
bibliography: references.bib
csl: mla.csl
citeproc: true
pdf-engine: xelatex
header-includes:
  - \usepackage{fontspec}
  - \setmainfont[ItalicFont=* Italic, BoldFont=* Bold, BoldItalicFont=* Bold Italic]{Equity A}
  - \setsansfont{Helvetica}
  - \setmonofont{Menlo}
---
```

Then the body:

```markdown
# Demo Document with All Citations

This document demonstrates Pandoc citations (MLA 9 via CSL).

@boylesModernMansGuide1987  
@hugoTriggeringTownLectures1979  
@kingWritingMemoirCraft2000  
@parkerRulesThumb1983  
@shakespeareHamlet1603  
@strunkElementsStyle1959  
@vonnegutMotherNight1962  
@vonnegutSlaughterhouseFiveChildrensCrusade1969  
@wagenvoordMansBookComplete1978  
@wallechinskyPeoplesAlmanacPresents1977  
@walshItsAllToo2006  
@wattsWisdomInsecurityMessage1951

# Font Sampler

Regular Equity, **Bold Equity**, *Italic Equity*, ***Bold Italic Equity***.

{\sffamily This line should be Helvetica (sans).}

{\ttfamily This line should be Menlo (mono).}
```

> Notes on **what those `@keys` do**:
> - `@key` (no brackets) = **in-text** citation (author text like “Boyles et al.”).
> - `[@key]` = **parenthetical** citation `(Boyles et al.)`.
> - To include something **in Works Cited without showing a citation in the text**, use the YAML trick:
>
>   ```yaml
>   nocite: |
>     @boylesModernMansGuide1987
>     @hugoTriggeringTownLectures1979
>     ...
>   ```
>
>   If you don’t want in-text citations at all, rely on `nocite:` (we omitted it today).

---

## 6) Build commands (two ways)

**Shortest path** (YAML carries the settings):

```sh
pandoc demo.md -o demo.pdf
```

**Explicit flags** (good for debugging):

```sh
pandoc demo.md   --bibliography=references.bib   --csl=mla.csl   --citeproc   --pdf-engine=xelatex   -o demo.pdf
```

---

## 7) Fonts & engines (what bit us and why)

### Why XeLaTeX (not pdflatex)
- `fontspec` (system fonts like Equity) **requires XeLaTeX or LuaLaTeX**.
- If Pandoc uses pdflatex you’ll see:
  ```
  fontspec Error: cannot-use-pdftex
  ```
  Fix by forcing the engine **both** in YAML (`pdf-engine: xelatex`) and on the CLI while testing (`--pdf-engine=xelatex`).

### Correct `fontspec` syntax
Use **`[options]{Font}`**, not `{Font}{[options]}`.

✅ Right:
```tex
\setmainfont[ItalicFont=* Italic, BoldFont=* Bold, BoldItalicFont=* Bold Italic]{Equity A}
```

❌ Wrong (caused “Missing \begin{document}” for us):
```tex
\setmainfont{Equity A}{[ItalicFont=* Italic, ...]}
```

### If a font isn’t found
- Keep **Equity** for main, but use macOS defaults for the rest:
  ```tex
  \setsansfont{Helvetica}
  \setmonofont{Menlo}
  ```
- To discover exact family names visible to XeLaTeX:
  ```sh
  fc-list | grep -i equity
  fc-list | grep -i concourse
  fc-list | grep -i triplicate
  ```

---

## 8) Verifying first publication dates (what to store)

What we cared about: **the first publication year** of each book. MLA cites the version you used, but if original dates matter for your notes:

- In Zotero, use **Edition** + **Date** for the copy you own/read.
- If you want to preserve the **original year**, add it in **Extra** as:
  ```
  original-date: 1969
  ```
  (CSL styles can surface this if configured; MLA normally does not print it by default.)

Keep the `.bib` honest—publisher and year should match the edition you’re citing. (We fixed publisher ampersands `\&`, and a stray spacing typo in “W. W. Norton”.)

---

## 9) Why you saw “Boyles et al. Hugo Parker …”

That string appears when you place **bare `@keys`** in the body. Pandoc renders those as **in-text** author citations. If you only want a bibliography:

- Use `nocite` in YAML (recommended), **or**
- Put the citations in an HTML comment so they don’t render (quick hack):
  ```markdown
  <!--
  @boylesModernMansGuide1987
  @hugoTriggeringTownLectures1979
  ...
  -->
  ```
- Or switch them to silent spans (e.g., a hidden div via CSS if you’re targeting HTML). For PDFs, `nocite` is the cleanest.

---

## 10) Inspect what Pandoc really sent to LaTeX

When confused, generate `.tex` and look:

```sh
pandoc demo.md -s --pdf-engine=xelatex -t latex -o demo.tex
open -a BBEdit demo.tex
```

Quick greps:

```sh
grep -n 'setmainfont' demo.tex
grep -n '{\[' demo.tex        # catches the bad {[ pattern
```

If `.tex` looks right but the PDF still fails, run `xelatex demo.tex` to see pure LaTeX errors.

---

## 11) Troubleshooting quick table

| Symptom                                                                 | Likely Cause                          | Fast Fix |
|---|---|---|
| `fontspec Error: cannot-use-pdftex`                                     | Pandoc used **pdflatex**              | Add `pdf-engine: xelatex` to YAML; also pass `--pdf-engine=xelatex`. |
| `Missing \begin{document}` pointing at a `\setmainfont` line            | Wrong braces: `{Font}{[options]}`     | Use `[options]{Font}` form. |
| `The font "Concourse T3" cannot be found`                               | Family name mismatch / not installed  | Use `Helvetica` / `Menlo`, or find exact name via `fc-list`. |
| “citation not found: KEY”                                               | `demo.md` keys ≠ keys in `references.bib` | List keys: `sed -n 's/^@[^ {]*{\([^,]*\),.*/\1/p' references.bib | sort` |
| YAML seems ignored                                                      | BOM/whitespace before `---`           | Ensure `---` is **first char**; save UTF-8 **without BOM**. |

---

## 12) Optional: external header (bypass YAML for fonts)

If the Markdown front matter gets finicky, push font setup to **`header.tex`**:

```tex
% header.tex
\usepackage{fontspec}
\setmainfont[ItalicFont=* Italic, BoldFont=* Bold, BoldItalicFont=* Bold Italic]{Equity A}
\setsansfont{Helvetica}
\setmonofont{Menlo}
```

Build with:

```sh
pandoc demo.md -H header.tex --pdf-engine=xelatex -o demo.pdf
```

---

## 13) Example Makefile (one-command builds)

```make
PDF=demo.pdf
MD=demo.md
BIB=references.bib
CSL=mla.csl

all: $(PDF)

$(PDF): $(MD) $(BIB) $(CSL)
	pandoc $(MD) 	  --bibliography=$(BIB) 	  --csl=$(CSL) 	  --citeproc 	  --pdf-engine=xelatex 	  -o $(PDF)

clean:
	rm -f $(PDF) demo.aux demo.log demo.out demo.tex
```

Usage:

```sh
make          # build
make clean    # tidy artifacts
```

---

## 14) Minimal test files (drop-in)

**`fonttest.md`** (sanity-check XeLaTeX + Equity):

```markdown
---
pdf-engine: xelatex
header-includes:
  - \usepackage{fontspec}
  - \setmainfont{Equity A}
---
Hello, Equity.
```

Build:

```sh
pandoc fonttest.md -o fonttest.pdf
```

**`demo.md`** (final working doc — see section 5).

---

## 15) What we accomplished (today’s fixes, summarized)

- Exported a clean **Better BibTeX** file with stable keys; corrected publisher escapes/typos.
- Chose a proper **MLA 9** CSL and confirmed default sorting behavior.
- Built **Pandoc + citeproc** pipeline that outputs MLA *Works Cited* from `references.bib`.
- Solved engine errors by forcing **XeLaTeX** (YAML + CLI).
- Fixed `fontspec` syntax (`[options]{Font}`), eliminating `\begin{document}` errors.
- Set **Equity** as main text face; used **Helvetica/Menlo** as reliable macOS fallbacks.
- Explained why bare `@keys` print author lists, and how to use **`nocite`** to include items silently.
- Added fast diagnostics: generate `.tex`, grep for `setmainfont`, detect `{[` typos, list bib keys, etc.

---

## 16) Replicate this later (checklist)

1. Install Pandoc + MacTeX; verify `xelatex`.
2. Export `.bib` from Zotero with Better BibTeX; pin keys.
3. Put `demo.md`, `references.bib`, and `mla.csl` in a folder.
4. Paste the YAML header from section **5** (Equity + fallbacks; `pdf-engine: xelatex`).
5. Add your `@keys` to the body (or use `nocite:`).
6. Run `pandoc demo.md -o demo.pdf` (or `make`).
7. If anything fails, jump to sections **7–12**.
