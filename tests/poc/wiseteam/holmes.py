"""Holmes - Inspark's S4 Diagnostic & Knowledge agent with confidential filter.

Core rule per Wise Team Intenture V#4 (data isolation):
- Holmes can read all data within a tenant boundary
- Holmes must NOT disclose raw confidential numbers of Clients or Inspark
- Aggregated / anonymized analytics are allowed

PoC filter: regex-based redaction of:
- Raw $-amounts >= $1000 (configurable)
- Specific Client revenue strings (when tagged as confidential)

Production fork: semantic filter via Claude (e.g., "is this output revealing
specific Client confidential data?" gate), per-Client policy, per-recipient
visibility rules.
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Pattern

from agno.agent import Agent
from agno.models.anthropic import Claude

HOLMES_RBAC_SCOPE = "holmes:diagnostics"

# Redact bare $-amounts of 4+ digits ($1000+) - PoC heuristic
_DOLLAR_PATTERN: Pattern[str] = re.compile(
    r"\$\s*(\d{1,3}(?:[,.\s]\d{3})+|\d{4,})(?:\.\d+)?\s*(?:USD|usd)?",
    flags=re.IGNORECASE,
)

# Explicit Client revenue annotations - PoC heuristic for "RAW" disclosures
_CLIENT_REVENUE_PATTERN: Pattern[str] = re.compile(
    r"(client\s+[A-Z0-9-]+\s*['\"]?s?\s+(?:revenue|MRR|ARR|profit|EBITDA)[^.]*)",
    flags=re.IGNORECASE,
)


@dataclass
class FilterReport:
    output: str
    redactions_count: int
    confidential_detected: bool


def confidential_filter(text: str) -> FilterReport:
    """Redact raw confidential numbers; allow aggregates and qualitative analysis."""
    if not text:
        return FilterReport(output=text or "", redactions_count=0, confidential_detected=False)

    redactions = 0

    def _redact_dollar(match: re.Match) -> str:
        nonlocal redactions
        redactions += 1
        return "[REDACTED]"

    redacted = _DOLLAR_PATTERN.sub(_redact_dollar, text)
    # Also redact explicit "Client X's revenue/MRR ..." constructs
    redacted, n2 = _CLIENT_REVENUE_PATTERN.subn(
        lambda m: "[REDACTED CLIENT FINANCIALS]", redacted
    )
    redactions += n2

    return FilterReport(
        output=redacted,
        redactions_count=redactions,
        confidential_detected=redactions > 0,
    )


class Holmes:
    """Tenant-scoped Holmes diagnostic agent.

    Each Holmes instance is bound to a single tenant_id. Cross-tenant
    queries are blocked at this layer (in addition to storage-level isolation).
    """

    AGENT_INSTRUCTIONS = (
        "You are Holmes - Inspark's diagnostic and knowledge agent. "
        "Provide analytical insights from data given to you. Be concise. "
        "You may discuss aggregate metrics (averages, totals across many entities) "
        "but you must NEVER reveal a specific single Client's raw revenue, MRR, "
        "or profit numbers in plain text. If asked for raw Client financials, "
        "respond that the data is confidential and offer aggregates instead."
    )

    def __init__(self, tenant_id: str, model_id: str = "claude-sonnet-4-5") -> None:
        self.tenant_id: str = tenant_id
        self.scope: str = HOLMES_RBAC_SCOPE
        self._agent = Agent(
            id=f"holmes-{tenant_id}",
            model=Claude(id=model_id),
            instructions=self.AGENT_INSTRUCTIONS,
            markdown=False,
        )

    def query(self, prompt: str, tenant_data: Optional[List[str]] = None) -> FilterReport:
        """Run a query scoped to this Holmes' tenant; apply confidential filter."""
        full_prompt = prompt
        if tenant_data:
            context = "\n".join(f"- {row}" for row in tenant_data)
            full_prompt = (
                f"Tenant '{self.tenant_id}' data:\n{context}\n\n"
                f"Query: {prompt}\n\n"
                f"Answer in 1-3 sentences."
            )
        raw = self._agent.run(full_prompt).content or ""
        return confidential_filter(raw)

    def cross_tenant_query_returns_empty(self, foreign_tenant_id: str) -> str:
        """Explicit safeguard: Holmes refuses queries about other tenants.

        Real production: this would be enforced by RBAC + tenant_id scoping at
        AgentOS API gateway. PoC mock: simple guard in this method.
        """
        if foreign_tenant_id != self.tenant_id:
            return ""  # empty == access denied / isolated
        return f"Data for tenant {self.tenant_id} accessible"
