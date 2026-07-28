import sys
from pathlib import Path
import pytest
import asyncio

# Make imports work whether pytest is run from backend/, backend/tests/, or workspace root.
BACKEND_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BACKEND_DIR / "src"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SRC_DIR))

# Disable litellm background logging queue to prevent event loop mismatch errors in asyncio tests
try:
    import litellm
    litellm.telemetry = False
    litellm.turn_off_message_logging = True
    if hasattr(litellm, "logging_worker"):
        litellm.logging_worker = None
except Exception:
    pass


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)
pytest.mark.asyncio = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(autouse=True)
def reset_city_agent_runtime_state():
    """Best-effort cleanup to keep ADK tests isolated across cases."""
    try:
        from city_agent import agent as city_agent_module

        city_agent_module.MAX_SEARCH_CALLS = 10
        city_agent_module.search_data_count = 0
        yield
        city_agent_module.MAX_SEARCH_CALLS = 10
        city_agent_module.search_data_count = 0
        city_agent_module.purge_cached_files()
    except Exception:
        # Some test modules do not import/run CityAgent; keep fixture non-blocking.
        yield


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Write a clean summary of all failed and errored tests at the end of test_run.log."""
    import logging

    logger = logging.getLogger("pytest_summary")
    failed_reports = terminalreporter.stats.get("failed", [])
    error_reports = terminalreporter.stats.get("error", [])
    reports = failed_reports + error_reports

    if not reports:
        logger.info("=========================================================================")
        logger.info("                  ALL TESTS PASSED SUCCESSFULLY                          ")
        logger.info("=========================================================================")
        return

    logger.error("=========================================================================")
    logger.error("                  TEST FAILURES & ERRORS SUMMARY                         ")
    logger.error("=========================================================================")
    for rep in reports:
        logger.error(f"FAIL/ERROR: {rep.nodeid}")
        if hasattr(rep, "longreprtext") and rep.longreprtext:
            for line in rep.longreprtext.splitlines():
                logger.error(f"  {line}")
    logger.error("=========================================================================")