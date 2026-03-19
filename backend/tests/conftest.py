import sys
from pathlib import Path
import pytest
import asyncio

# Make imports work whether pytest is run from backend/, backend/tests/, or workspace root.
BACKEND_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BACKEND_DIR / "src"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SRC_DIR))

# Fix event loop issues with litellm and pytest-asyncio
@pytest.fixture(scope="session")
def event_loop_policy():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="session")
def event_loop(event_loop_policy):
    loop = event_loop_policy.new_event_loop()
    yield loop
    loop.close()


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