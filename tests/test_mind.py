import tempfile
import unittest
from pathlib import Path

from ultron_mind import MindCorpus


class MindCorpusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.mind = MindCorpus(Path(self.temp.name) / "mind.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_original_and_derivation_remain_separate(self):
        entry = self.mind.record("Decidi manter o núcleo independente.", speaker="user")
        self.mind.derive(entry, "Decisão arquitetural: núcleo desacoplado.", agent="ultron")
        result = self.mind.context_for("núcleo")[0]
        self.assertEqual(result["content"], "Decidi manter o núcleo independente.")
        self.assertEqual(result["derivations"][0]["content"], "Decisão arquitetural: núcleo desacoplado.")

    def test_revision_appends_instead_of_overwriting(self):
        first = self.mind.record("Plano inicial", kind="decision")
        second = self.mind.record("Plano revisado", kind="decision", supersedes_id=first)
        self.assertEqual(len(self.mind.timeline()), 2)
        self.assertEqual(self.mind.timeline()[1]["supersedes_id"], first)
        self.assertNotEqual(first, second)

    def test_links_tags_and_integrity(self):
        a = self.mind.record("Projeto A")
        b = self.mind.record("Projeto B")
        self.mind.tag(a, " Projetos   principais ", agent="ultron")
        self.mind.link(a, b, relation="related_to")
        self.assertEqual(self.mind.context_for("Projeto A")[0]["tags"], ["projetos principais"])
        self.assertTrue(self.mind.verify_integrity()["valid"])

    def test_rejects_invalid_limits_and_missing_sources(self):
        with self.assertRaises(ValueError):
            self.mind.search("x", limit=0)
        with self.assertRaises(ValueError):
            self.mind.derive(999, "summary", agent="ultron")
        with self.assertRaises(ValueError):
            self.mind.record(" ")

    def test_integrity_detects_modified_source(self):
        entry = self.mind.record("texto original")
        with self.mind._connect() as db:
            db.execute("UPDATE mind_entries SET content='texto adulterado' WHERE id=?", (entry,))
        self.assertFalse(self.mind.verify_integrity()["valid"])


if __name__ == "__main__":
    unittest.main()
