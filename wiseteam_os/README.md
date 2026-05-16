# Wise Team OS

Agno AgentOS deployment with three teams across three tenants:

| Team | Agents | Purpose |
|------|--------|---------|
| **Wise Team** | Vergil | Platform-tier - Intenture explication per In++ 2.0 |
| **Inspark AI-Team** | Nick, Willie, Holmes | Inspark CVD pipeline (phases 0-5) |
| **Outlive** | Haizel, Ethan, Luka, Thea, Augst | Personal health team (sternlieb.ai) |

All 9 agents use Claude Sonnet 4.5. Health agent instructions come from
Anthropic skill SKILL.md files copied into `agents/skills_md/`. Multi-tenancy
is enforced through `user_id` scoping in the shared DB layer.

## Run locally

```bash
# From repo root
.venv/bin/python -m wiseteam_os.main
```

Open https://os.agno.com, sign in, add a workspace pointing at
`http://localhost:7777` - you'll see all 9 agents and 3 teams.

Or hit the REST API directly:

```bash
curl http://localhost:7777/config             # introspect what's deployed
curl -X POST http://localhost:7777/agents/vergil/runs \
  -F "message=Представься в одном предложении" -F "stream=false"
```

## Run in production (Railway)

1. Sign in at https://railway.app
2. **New Project -> Deploy from GitHub repo -> shternlib/wise-team**
3. Add a **Postgres** plugin in the project; Railway auto-injects `DATABASE_URL`
4. Add env var: `ANTHROPIC_API_KEY=sk-ant-...`
5. Railway uses `Dockerfile` + `railway.toml` at the repo root to build and run
6. Open the assigned `*.up.railway.app` URL. Connect from https://os.agno.com.

The app uses Postgres when `DATABASE_URL` is set, SQLite otherwise.

## Structure

```
wiseteam_os/
├── main.py                       # AgentOS app + agents/teams composition
├── requirements.txt              # production dependencies
├── README.md
└── agents/
    ├── wiseteam_agents.py        # Vergil
    ├── inspark_agents.py         # Nick, Willie, Holmes
    ├── outlive_agents.py         # Haizel, Ethan, Luka, Thea, Augst
    └── skills_md/                # Anthropic skill SKILL.md (system prompts)
        ├── cardiologist.md
        ├── endocrinologist.md
        ├── fitness-trainer.md
        └── nutritionist.md
```

## Safety / disclaimers

- Outlive agents are AI giving general information, not licensed medical advice.
  Each agent's prompt instructs it to recommend professional consultation for
  diagnosis or prescription.
- Holmes (Inspark) never reveals raw confidential Client financial numbers in
  plain text - only aggregates.
- Telemetry is permanently disabled (`AGNO_TELEMETRY=false`).
