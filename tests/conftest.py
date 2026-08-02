import os

import pytest

os.environ.setdefault("RH_API_OFFLINE_TOKEN", "test-token")


@pytest.fixture(autouse=True)
def _reset_client():
    """Reset the global client singleton between tests."""
    from redhat_api_mcp import tools
    tools._client = None
    yield
    tools._client = None
