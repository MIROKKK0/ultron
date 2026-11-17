import tempfile
import unittest
from pathlib import Path

from skills_manager import SkillsManager


class SkillsManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.builtin = self.root / "builtin"
        self.user = self.root / "user"
        (self.builtin / "demo").mkdir(parents=True)
        (self.builtin / "demo" / "SKILL.md").write_text(
            "---\nname: demo\ndescription: Example skill\n---\n\nInstructions here.",
            encoding="utf-8",
        )
        self.manager = SkillsManager(self.builtin, self.user)

    def tearDown(self):
        self.temp.cleanup()

    def test_lists_builtin_skill(self):
        skills = self.manager.list_skills()
        self.assertEqual([item["name"] for item in skills], ["demo"])
        self.assertEqual(skills[0]["description"], "Example skill")

    def test_loads_skill_body(self):
        self.assertEqual(self.manager.load_skill("demo"), "Instructions here.")

    def test_rejects_invalid_skill_name(self):
        self.assertEqual(self.manager.load_skill("../secrets"), "Nome de skill inválido.")

    def test_unknown_skill_is_reported(self):
        self.assertEqual(self.manager.load_skill("missing"), "Skill não encontrada: missing")


if __name__ == "__main__":
    unittest.main()
