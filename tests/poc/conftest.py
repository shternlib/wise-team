"""Shared pytest fixtures for Wise Team PoC test suite."""
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).parent.parent.parent


def pytest_configure(config):
    """Load .env once for the whole session, override existing empty env vars."""
    load_dotenv(REPO_ROOT / ".env", override=True)
    # Wise Team policy: telemetry off
    os.environ.setdefault("AGNO_TELEMETRY", "false")


@pytest.fixture(scope="session")
def claude_model_id() -> str:
    """Model used for PoC tests (cost-efficient)."""
    return "claude-sonnet-4-5"
