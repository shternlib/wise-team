# Wise Team PoC — fork of Agno

This is a **Proof-of-Concept fork** of [agno-agi/agno](https://github.com/agno-agi/agno) (Apache 2.0).

## Purpose

Validate Agno as a production foundation for **Wise Team** - a WISE-organization-level
operational platform for AI-employee teams, with first application on Inspark
(influencer marketing agency, 11 AI-agents executing CVD - Client Value Delivery).

Go/No-Go decision in 4 weeks based on 22 acceptance criteria (12 HARD + 10 SOFT)
covering 6 test categories.

See full test plan: https://inspark.wiseorg.io/docs/agno-test-plan.html

## Reference Artifacts

- **Wise Team Intenture** (canonical In++ 2.0): https://inspark.wiseorg.io/wiseteam/wise-team
- **Inspark AI-Team Intenture**: https://inspark.wiseorg.io/wiseteam/inspark-ai-team
- **Architecture Decision Record (v1.1)**: https://inspark.wiseorg.io/docs/wiseteam-architecture-analysis.html
- **Test Plan (v1.0)**: https://inspark.wiseorg.io/docs/agno-test-plan.html

## Stages

| Stage | Status | Deliverable |
|-------|--------|-------------|
| 0 · Setup | ✓ done | Fork, dev env, telemetry off, PoC marker |
| 1 · Smoke | ✓ done | Hello-world Agno + Claude e2e |
| 2 · MUST tests (A1-A4) | ✓ done | A1 ✓ Protocol Ext. · A2 ✓ Multi-tenant · A3 ✓ Observability · A4 ✓ Tools/MCP (17/17 tests pass, ~80s) |
| 3 · In++ Layer | ⏳ | CI/SP/IRS/TB/PB as Pydantic schemas |
| 4 · Vergil S2 | ⏳ | Built-in coordinator agent |
| 5 · CVD scenarios (B) | ⏳ | Nick + Mr.Wolf + Vergil, CVD 0-2 e2e |
| 6 · Tenant security (C) | ⏳ | Holmes filter, 0 cross-leak |
| 7 · D, E, F | ⏳ | Self-evolution / Load / Fork-ability |
| 8 · Decision Gate | ⏳ | 22 criteria audit, Go/No-Go report |

## Deviations from upstream Agno

This fork will diverge from `agno-agi/agno` on:

1. **Vergil as built-in S2 WISE coordinator** (new agent class, RBAC scope `vergil:coordinator`)
2. **In++ 2.0 Realization Artifacts layer** (Pydantic schemas + validator + middleware)
3. **Lifecycle FSM** (Dream → Exploratory → Explicated → Structured → Realizable → In Realization → Evolving → Archived)
4. **Telemetry permanently disabled** (`AGNO_TELEMETRY=false` enforced)

Upstream merges tested in stage 7 (F2).

## License

Apache 2.0 (inherited from upstream Agno). See `LICENSE`.

## How to run

```bash
# Setup
./scripts/dev_setup.sh    # creates .venv with Python 3.12
cp .env.example .env       # fill in API keys

# Smoke test
source .venv/bin/activate
python cookbook/01_introduction/01_agent_with_tools.py
```
