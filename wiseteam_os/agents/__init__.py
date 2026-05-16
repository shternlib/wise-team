"""Agent factories for the three Wise Team OS tenants.

Each factory takes the shared SqliteDb and returns a configured Agent.
Instructions for health agents come from Anthropic skill SKILL.md files
copied into skills_md/.
"""
from pathlib import Path

SKILLS_DIR = Path(__file__).parent / "skills_md"


def load_skill(name: str) -> str:
    """Read a SKILL.md as plain text for use as agent system prompt."""
    return (SKILLS_DIR / f"{name}.md").read_text(encoding="utf-8")
