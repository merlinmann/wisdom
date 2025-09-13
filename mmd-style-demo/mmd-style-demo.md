Title: MultiMarkdown Style Demo (All-in-One)
Author: Merlin Mann
Date: 2025-09-13
Keywords: demo, test, MultiMarkdown, Marked 2
Base Header Level: 1
TOC: true

<!--
  All-in-one demo: MultiMarkdown content + inline CSS for Marked 2.
  Notes:
  - Inline <style> is included below so you don’t need a separate .css file.
  - Marked renders inside a #wrapper div; the CSS targets that.
  - Toggle your OS dark mode to preview the dark palette.
-->





# Overview [#overview]

This document exercises **MultiMarkdown** and Marked 2 features: metadata, headings, links, images/figures (with captions), tables (with alignment and captions), footnotes,[^fn-intro] definition lists, math, CriticMarkup, and cross-references (e.g., see [Overview](#overview) and jump to [Tables](#tables)).

> Tip: Resize the window and toggle light/dark mode to preview the CSS variables.


----



## Contents [#contents]

{{TOC}}


---

## Headings, Paragraphs, and Text [#text]

Regular paragraph with smart quotes (“quoted”), dashes (en–dash, em—dash), and ellipses… along with *emphasis*, **strong**, `inline code`, and small caps via HTML: <span style="font-variant-caps: small-caps;">Small Caps</span>.

- Unordered list
	- Nested item
- Another bullet

----


1. Ordered list
1. Second item
	1. Nested ordered

----


Task list:

- [x] Done item
- [ ] Pending item


----


> Blockquote with two paragraphs to check spacing.
>
> Second paragraph stays tight.

Horizontal rule below:

----

## Links and Cross-References [#links]

External link: <https://marked2app.com>.  
Reference link: [Marked Home][marked].  
Cross-reference to [Tables](#tables).

[marked]: https://marked2app.com "Marked 2"

Abbreviations (Markdown Extra style):

*[HTML]: HyperText Markup Language
*[CSS]: Cascading Style Sheets

HTML and CSS should render the tooltips when hovered.

## Images and Figures [#figures]

Figure caption via MultiMarkdown:

Figure: A remote image with a caption and width attribute

![Placeholder diagram](https://placehold.co/800x400/png)

Remote image with title:

![Estelle Getty - Wikipedia](https://upload.wikimedia.org/wikipedia/commons/9/98/EstelleGetty2.jpg "You Look Nice Today may have had a role in Ms. Getty's death.")

You can also reference figures: see [Figure 1](#figure-1) and [Figure 2](#figure-2).  
(Marked auto-numbers “Figure:” captions when exporting.)

## Code Blocks and Syntax Highlighting [#code]

Fenced code with language hint:

```javascript
// Simple demo
function greet(name) {
  console.log(`Hello, ${name}!`);
}
greet("Merlin");

```

## La Bas [#bottom]


- Boyles, Denis, Alan Rose, and Alan Wellikoff. *The Modern Man’s Guide to Life*. Harper & Row, 1987.  
- Hugo, Richard. *The Triggering Town: Lectures and Essays on Poetry and Writing*. W. W. Norton & Company, 1979.  
- King, Stephen. *On Writing: A Memoir of the Craft*. Scribner, 2000.  
- Parker, Tom. *Rules of Thumb*. Houghton Mifflin, 1983.  
- Shakespeare, William. *Hamlet*. First Quarto, 1603.  
- Strunk, William, Jr., and E. B. White. *The Elements of Style*. Macmillan, 1959.  
- Vonnegut, Kurt. *Mother Night*. Harper & Row, 1962.  
- ———. *Slaughterhouse-Five; or, The Children’s Crusade: A Duty-Dance with Death*. Delacorte Press, 1969.  
- Wagenvoord, James, and Peyton Bailey Budinger. *The Man’s Book: A Complete Manual of Style*. Avon Books, 1978.  
- Wallechinsky, David, Irving Wallace, and Amy Wallace. *The People’s Almanac Presents the Book of Lists*. William Morrow, 1977.  
- Walsh, Peter. *It’s All Too Much: An Easy Plan for Living a Richer Life with Less Stuff*. Free Press, 2006.  
- Watts, Alan W. *The Wisdom of Insecurity: A Message for an Age of Anxiety*. Pantheon Books, 1951.  

