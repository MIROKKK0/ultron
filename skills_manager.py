"""Local skill discovery and safe loading for Ultron.

Skills are instruction files (SKILL.md), not executable plugins. Installing or
running third-party code is deliberately kept outside this loader.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class SkillsManager:
    def __init__(self, builtin_dir: Optional[Path] = None,
                 user_dir: Optional[Path] = None):
        self.builtin_dir = builtin_dir or Path(__file__).parent / "skills"
        self.user_dir = user_dir or (Path.home() / ".ultron" / "skills")

    @staticmethod
    def _metadata(path: Path) -> Dict[str, str]:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return {"name": path.parent.name, "description": ""}
        end = text.find("\n---", 3)
        if end < 0:
            return {"name": path.parent.name, "description": ""}
        data: Dict[str, str] = {}
        for line in text[3:end].splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip().strip("\\\"'")
        data["_body"] = text[end + 4:].strip()
        return data

    def _skill_files(self) -> List[Path]:
        found = {}
        for root in (self.builtin_dir, self.user_dir):
            if root.exists():
                for path in root.glob("**/SKILL.md"):
                    if path.is_file():
                        found[path.parent.name] = path
        return list(found.values())

    def list_skills(self) -> List[Dict[str, str]]:
        skills = []
        for path in self._skill_files():
            try:
                meta = self._metadata(path)
                skills.append({
                    "name": meta.get("name", path.parent.name),
                    "description": meta.get("description", ""),
                    "source": str(path),
                })
            except (OSError, UnicodeError):
                continue
        return sorted(skills, key=lambda item: item["name"].lower())

    def load_skill(self, name: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", name):
            return "Nome de skill inválido."
        for path in self._skill_files():
            try:
                meta = self._metadata(path)
                if meta.get("name") == name or path.parent.name == name:
                    return meta.get("_body", "") or "Skill sem instruções."
            except (OSError, UnicodeError):
                continue
        return f"Skill não encontrada: {name}"

    def find_external(self, query: str) -> str:
        query = query.strip()
        if not query or len(query) > 200:
            return "Informe uma busca entre 1 e 200 caracteres."
        try:
            result = subprocess.run(
                ["npx", "--yes", "skills", "find", query],
                capture_output=True, text=True, timeout=90, check=False
            )
        except FileNotFoundError:
            return ("Node.js/npx não está instalado. Para pesquisar manualmente, "
                    "use: npx skills find " + query)
        except subprocess.TimeoutExpired:
            return "A busca de skills excedeu 90 segundos."
        output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
        return output.strip() or f"Busca encerrada sem resultados (código {result.returncode})."
