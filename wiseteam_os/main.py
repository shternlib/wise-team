"""Wise Team OS - AgentOS deployment with 3 teams across 3 tenants.

Run locally:
    .venv/bin/python -m wiseteam_os.main

Then connect a UI to http://localhost:7777:
- Hosted: https://os.agno.com (sign in -> add localhost workspace)
- Self-hosted: any client that speaks AgentOS REST/SSE

Production (Railway): see Dockerfile + railway.toml.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root before importing agno
REPO_ROOT = Path(__file__).parent.parent
load_dotenv(REPO_ROOT / ".env", override=True)

# Wise Team policy: telemetry off
os.environ.setdefault("AGNO_TELEMETRY", "false")

from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from agno.os import AgentOS
from agno.team import Team

from wiseteam_os.agents.inspark_agents import (
    build_holmes, build_nick, build_willie,
)
from wiseteam_os.agents.outlive_agents import (
    build_augst, build_ethan, build_haizel, build_luka, build_thea,
)
from wiseteam_os.agents.wiseteam_agents import build_vergil


# ─── Database ─────────────────────────────────────────────────────────
# Single SqliteDb backs all 9 agents - multi-tenancy via user_id scoping.
# Production: swap for PostgresDb pointing at Railway/Supabase.
DB_PATH = REPO_ROOT / "wiseteam_os" / "wiseteam_os.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL")  # Postgres URL if set (Railway etc)

if DATABASE_URL and DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+psycopg")):
    from agno.db.postgres import PostgresDb
    db = PostgresDb(id="wiseteam-os-db", db_url=DATABASE_URL)
else:
    db = SqliteDb(db_file=str(DB_PATH))


# ─── Build agents ─────────────────────────────────────────────────────

# Wise Team tier
vergil = build_vergil(db)

# Inspark tier
nick = build_nick(db)
willie = build_willie(db)
holmes = build_holmes(db)

# Outlive tier
haizel = build_haizel(db)
ethan = build_ethan(db)
luka = build_luka(db)
thea = build_thea(db)
augst = build_augst(db)


# ─── Build teams ──────────────────────────────────────────────────────

COORDINATOR_MODEL = Claude(id="claude-sonnet-4-5")

wiseteam_team = Team(
    id="wiseteam",
    name="Wise Team",
    description=(
        "Platform-tier team for WISE-organization. Vergil coordinates intent "
        "explication and Realization Artifacts. Future: + Architect."
    ),
    model=COORDINATOR_MODEL,
    db=db,
    members=[vergil],
    add_history_to_context=True,
    update_memory_on_run=True,
    markdown=True,
)

inspark_team = Team(
    id="inspark-ai-team",
    name="Inspark AI-Team",
    description=(
        "Inspark agency CVD pipeline: Nick (Client Cognition & Strategy, phases 0-2), "
        "Willie (Copywriter & Scenarios), Holmes (Diagnostics & Knowledge)."
    ),
    model=COORDINATOR_MODEL,
    db=db,
    members=[nick, willie, holmes],
    add_history_to_context=True,
    update_memory_on_run=True,
    markdown=True,
)

outlive_team = Team(
    id="outlive",
    name="Outlive",
    description=(
        "Personal health team (sternlieb.ai): Haizel (endocrinologist), "
        "Ethan (cardiologist), Luka (nutritionist), Thea (fitness trainer), Augst (chef). "
        "AI agents giving general info; not licensed medical advice."
    ),
    model=COORDINATOR_MODEL,
    db=db,
    members=[haizel, ethan, luka, thea, augst],
    add_history_to_context=True,
    update_memory_on_run=True,
    markdown=True,
)


# ─── AgentOS app ──────────────────────────────────────────────────────

agent_os = AgentOS(
    description="Wise Team OS - 3 tenants on shared platform (Wise Team / Inspark / Outlive)",
    agents=[vergil, nick, willie, holmes, haizel, ethan, luka, thea, augst],
    teams=[wiseteam_team, inspark_team, outlive_team],
)
app = agent_os.get_app()


if __name__ == "__main__":
    """Run AgentOS.

    Config endpoint: http://localhost:7777/config
    UI control plane: https://os.agno.com (add workspace -> http://localhost:7777)
    """
    agent_os.serve(app="wiseteam_os.main:app", reload=False, port=7777)
