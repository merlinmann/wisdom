"""Guard edition rollover and the boundary between authored and generated pages."""
import unittest
import shutil

from build_books import copyright_page, split_front_matter, markdown_edition


class FrontMatterTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc is installed before building books")
    def test_markdown_contents_reaches_the_named_section(self):
        source = '''<h1>Title</h1><h2>Contents</h2>
<p><a href="#intro">Introduction</a> <a href="#licensing-legalese">License</a>
<a href="#source-chesterton">G. K. C.</a></p>
<section id="intro"><h2>Introduction</h2><p>Opening text.</p></section>
<section id="licensing-legalese"><h2>Licensing &amp; Legalese</h2><p>Terms.</p></section>
<section id="works-cited"><h2>Works Cited</h2>
<div id="source-chesterton"><p>Chesterton. The Thing.</p></div></section>'''
        result = markdown_edition(source)
        self.assertIn("[Introduction](#introduction)", result)
        self.assertIn("[License](#licensing--legalese)", result)
        self.assertIn("[G. K. C.](#works-cited)", result)
        self.assertNotIn("<div", result)

    def test_edition_and_date_roll_over_without_editing_template(self):
        metadata = {"title": "A & B", "author": "An Author"}
        december = copyright_page(metadata, "2026.19", "2026-12-31", print_edition=True)
        january = copyright_page(metadata, "2027.1", "2027-01-01", print_edition=False)
        self.assertIn("Digital edition 2026.19", december)
        self.assertIn("December 31, 2026", december)
        self.assertIn("Digital edition 2027.1", january)
        self.assertIn('datetime="2027-01-01">January 1, 2027', january)
        self.assertNotIn("2026", january)
        self.assertIn("A &amp; B", january)
        self.assertNotIn("Set in Source Serif", january)

    def test_split_preserves_authored_content_and_stops_at_epigraphs(self):
        source = "# Title\n\nBy Author.\n\n----\n\n## Epigraphs\n\n> An epigraph.\n\n----\n\n## Main Text\n\nAdvice.\n"
        title, body = split_front_matter(source)
        self.assertIn("By Author.", title)
        self.assertNotIn("----", title)
        self.assertTrue(title.startswith("# Title\n"))
        self.assertEqual(body, source[source.index("## Epigraphs"):])
        with self.assertRaises(AssertionError):
            split_front_matter(source.replace("## Epigraphs", "## Dedication\n\n## Epigraphs"))


if __name__ == "__main__":
    unittest.main()
