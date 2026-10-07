import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "logseq-second-brain.html"
GRAPH = ROOT / "logseq-demo"


class DeckParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.top_level_slides = 0
        self.slide_ids = []
        self.local_assets = []
        self.notes = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "div" and "slides" in attributes.get("class", "").split():
            self.depth = 1
        elif self.depth and tag == "section":
            if self.depth == 1:
                self.top_level_slides += 1
                self.slide_ids.append(attributes.get("id"))
            self.depth += 1
        elif self.depth and tag == "aside" and "notes" in attributes.get("class", "").split():
            self.notes += 1

        for attribute in ("src", "href"):
            value = attributes.get(attribute, "")
            if value and not value.startswith(("http://", "https://", "#", "data:")):
                self.local_assets.append(value.split("?", 1)[0])

    def handle_endtag(self, tag):
        if self.depth and tag == "section":
            self.depth -= 1
        elif self.depth == 1 and tag == "div":
            self.depth = 0


class LogseqSecondBrainTest(unittest.TestCase):
    def test_deck_has_twelve_named_slides_with_speaker_notes(self):
        self.assertTrue(DECK.exists(), "the Reveal.js deck is missing")
        parser = DeckParser()
        parser.feed(DECK.read_text(encoding="utf-8"))

        self.assertEqual(parser.top_level_slides, 12)
        self.assertEqual(len(set(parser.slide_ids)), 12)
        self.assertNotIn(None, parser.slide_ids)
        self.assertGreaterEqual(parser.notes, 10)

    def test_every_local_deck_asset_exists(self):
        self.assertTrue(DECK.exists(), "the Reveal.js deck is missing")
        parser = DeckParser()
        parser.feed(DECK.read_text(encoding="utf-8"))

        missing = sorted({asset for asset in parser.local_assets if not (ROOT / asset).exists()})
        self.assertEqual(missing, [])

    def test_graph_contains_contextual_tasks_and_each_priority_level(self):
        journals = sorted((GRAPH / "journals").glob("*.md"))
        self.assertGreaterEqual(len(journals), 5)

        tasks = []
        for journal in journals:
            tasks.extend(
                line.strip()
                for line in journal.read_text(encoding="utf-8").splitlines()
                if re.match(r"^- (TODO|DOING|DONE)\b", line.strip())
            )

        self.assertGreaterEqual(len(tasks), 12)
        self.assertTrue(all("[[" in task or "#" in task for task in tasks))
        self.assertTrue(any("[#A]" in task for task in tasks))
        self.assertTrue(any("[#B]" in task for task in tasks))
        self.assertTrue(any("[#C]" in task for task in tasks))
        self.assertTrue(any("TODO" in task and "[#" not in task for task in tasks))
        journal_text = "\n".join(journal.read_text(encoding="utf-8") for journal in journals)
        self.assertIn("DEADLINE:", journal_text)

    def test_graph_has_dashboard_contacts_notes_and_realistic_incident(self):
        contents_page = GRAPH / "pages" / "Contents.md"
        self.assertTrue(contents_page.exists(), "the Logseq Contents page is missing")
        pages = list((GRAPH / "pages").glob("*.md"))
        contents = contents_page.read_text(encoding="utf-8")
        graph_text = "\n".join(page.read_text(encoding="utf-8") for page in pages)
        graph_text += "\n" + "\n".join(
            journal.read_text(encoding="utf-8") for journal in (GRAPH / "journals").glob("*.md")
        )

        self.assertGreaterEqual(contents.count("{{query"), 5)
        self.assertIn("👤 Contacts", graph_text)
        self.assertIn("📝 Notes", graph_text)
        self.assertRegex(graph_text, r"Starlink[- ]35956")

    def test_graph_does_not_override_the_journal_home_page(self):
        config_path = GRAPH / "logseq" / "config.edn"
        config = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        self.assertNotIn(":default-home", config)

    def test_graph_has_no_case_colliding_contents_page(self):
        matches = sorted(
            page.name
            for page in (GRAPH / "pages").glob("*.md")
            if page.name.casefold() == "contents.md"
        )
        self.assertEqual(matches, ["Contents.md"])


if __name__ == "__main__":
    unittest.main()
