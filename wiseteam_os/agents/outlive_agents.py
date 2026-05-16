"""Outlive (sternlieb.ai) personal health team - 5 agents.

Haizel  - endocrinologist
Ethan   - cardiologist
Luka    - nutritionist
Thea    - fitness trainer
Augst   - chef

Health agent instructions are loaded from Anthropic skill SKILL.md files
copied into skills_md/. Augst (chef) uses a custom prompt - no chef skill exists.

Safety/legal disclaimer: these are AI agents giving general information, not
medical advice. Each agent is prompted to recommend professional consultation
for diagnosis and prescription.
"""
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude

from . import load_skill


def _wrap_with_persona(name: str, role_ru: str, base_instructions: str, extra: str = "") -> str:
    """Wrap a skill's instructions with Outlive-specific persona and team context."""
    return f"""\
You are {name} - a member of the Outlive personal health team caring for the user
("Theimur") together with 4 other specialists. You speak Russian or English depending
on the user's language. Be concise, evidence-based, and warm.

Your role in the team: {role_ru}.

Always remember:
- You are an AI, not a licensed medical professional. For diagnosis, prescription,
  or treatment decisions, recommend the user consult a licensed doctor in their
  jurisdiction (the user is based in Russia / Cyprus / EU - tailor recommendations
  accordingly).
- Coordinate with teammates when their domain is involved (Luka for nutrition,
  Thea for exercise, Augst for cooking, Ethan for cardiac, Haizel for hormones).
- Reference shared user context (age, current metrics, history) when available.

Your specialist instructions:

{base_instructions}

{extra}
"""


def build_haizel(db: SqliteDb) -> Agent:
    instructions = _wrap_with_persona(
        name="Haizel",
        role_ru="endocrinologist - hormones, metabolism, thyroid, insulin, blood glucose",
        base_instructions=load_skill("endocrinologist", with_references=True),
    )
    return Agent(
        id="haizel", name="Haizel",
        model=Claude(id="claude-sonnet-4-5"),
        instructions=instructions,
        description="Outlive - Endocrinologist (hormones, metabolism)",
        db=db,
        enable_session_summaries=True, update_memory_on_run=True,
        add_history_to_context=True, num_history_runs=5,
        add_datetime_to_context=True, markdown=True,
    )


def build_ethan(db: SqliteDb) -> Agent:
    instructions = _wrap_with_persona(
        name="Ethan",
        role_ru="cardiologist - heart, vessels, blood pressure, cholesterol, cardio risk",
        base_instructions=load_skill("cardiologist"),
    )
    return Agent(
        id="ethan", name="Ethan",
        model=Claude(id="claude-sonnet-4-5"),
        instructions=instructions,
        description="Outlive - Cardiologist (heart and vessels)",
        db=db,
        enable_session_summaries=True, update_memory_on_run=True,
        add_history_to_context=True, num_history_runs=5,
        add_datetime_to_context=True, markdown=True,
    )


def build_luka(db: SqliteDb) -> Agent:
    instructions = _wrap_with_persona(
        name="Luka",
        role_ru="nutritionist - macronutrients, micronutrients, meal planning, food sensitivities",
        base_instructions=load_skill("nutritionist"),
    )
    return Agent(
        id="luka", name="Luka",
        model=Claude(id="claude-sonnet-4-5"),
        instructions=instructions,
        description="Outlive - Nutritionist (diet, macro/micronutrients)",
        db=db,
        enable_session_summaries=True, update_memory_on_run=True,
        add_history_to_context=True, num_history_runs=5,
        add_datetime_to_context=True, markdown=True,
    )


def build_thea(db: SqliteDb) -> Agent:
    instructions = _wrap_with_persona(
        name="Thea",
        role_ru="fitness trainer - strength, cardio, mobility, recovery, programming",
        base_instructions=load_skill("fitness-trainer"),
    )
    return Agent(
        id="thea", name="Thea",
        model=Claude(id="claude-sonnet-4-5"),
        instructions=instructions,
        description="Outlive - Fitness Trainer (strength, cardio, mobility)",
        db=db,
        enable_session_summaries=True, update_memory_on_run=True,
        add_history_to_context=True, num_history_runs=5,
        add_datetime_to_context=True, markdown=True,
    )


AUGST_INSTRUCTIONS = _wrap_with_persona(
    name="Augst",
    role_ru="chef - cooking, recipes, meal preparation that aligns with Luka's nutritional guidance",
    base_instructions="""\
You are a professional chef specializing in healthy, flavorful, practical home
cooking. You translate nutritional targets into actual delicious recipes.

When the user asks for meals:
- Always ask about cuisine preference (Mediterranean / Russian / Asian / etc.)
  if not specified, and dietary restrictions.
- Provide recipes with: ingredients (metric units), prep time, cooking time,
  difficulty (easy / medium / hard), key nutritional notes
  (calories, protein, carbs, fat per serving).
- Coordinate with Luka: if a meal plan exists, propose recipes that hit the
  macros without exceeding bounds.
- Suggest substitutions for allergies, dislikes, or missing ingredients.
- Favor whole foods, minimal processing, seasonal produce.

When making suggestions, structure as: brief name -> why it fits -> recipe -> tips.
""",
)


def build_augst(db: SqliteDb) -> Agent:
    return Agent(
        id="augst", name="Augst",
        model=Claude(id="claude-sonnet-4-5"),
        instructions=AUGST_INSTRUCTIONS,
        description="Outlive - Chef (recipes aligned with nutrition targets)",
        db=db,
        enable_session_summaries=True, update_memory_on_run=True,
        add_history_to_context=True, num_history_runs=5,
        add_datetime_to_context=True, markdown=True,
    )
