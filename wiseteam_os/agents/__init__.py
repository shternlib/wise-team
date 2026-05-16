"""Agent factories for the three Wise Team OS tenants.

Each factory takes the shared SqliteDb and returns a configured Agent.
Instructions for health agents come from Anthropic skill SKILL.md files
copied into skills_md/.

Two skill layouts supported:
  1. Flat file: skills_md/<name>.md
  2. Skill dir: skills_md/<name>_ref/SKILL.md  + skills_md/<name>_ref/reference/*.md

The directory form is used when a skill has reference files; we inline them
into the system prompt. For very large reference sets (>~80KB total) move to
agno.knowledge (RAG) instead - this loader is the simple/fast path.
"""
from pathlib import Path

SKILLS_DIR = Path(__file__).parent / "skills_md"


def load_skill(name: str, with_references: bool = False) -> str:
    """Load a skill as a single system-prompt string.

    Args:
        name: Skill base name. Looks for <name>.md (flat) or <name>_ref/ (dir).
        with_references: If True and skill is in directory form, append
            reference/*.md content tagged by file name.
    """
    flat = SKILLS_DIR / f"{name}.md"
    if flat.exists() and not with_references:
        return flat.read_text(encoding="utf-8")

    skill_dir = SKILLS_DIR / f"{name}_ref"
    if skill_dir.is_dir():
        parts = [(skill_dir / "SKILL.md").read_text(encoding="utf-8")]
        ref_dir = skill_dir / "reference"
        if ref_dir.is_dir():
            parts.append("\n\n---\n\n# REFERENCE MATERIAL\n\nThe sections below are reference material you may consult when relevant to the user's question. Cite by section name when used.\n")
            for ref_file in sorted(ref_dir.glob("*.md")):
                parts.append(f"\n## REFERENCE: {ref_file.stem}\n\n{ref_file.read_text(encoding='utf-8')}\n")
        return "".join(parts)

    if flat.exists():
        return flat.read_text(encoding="utf-8")

    raise FileNotFoundError(
        f"Skill {name!r} not found. Looked for {flat} and {skill_dir}/SKILL.md"
    )
