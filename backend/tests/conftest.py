import sys
from pathlib import Path
import pytest
import asyncio

# Add src to path so tests can import from it
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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