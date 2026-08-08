import os

import pytest

os.environ.setdefault("RH_API_OFFLINE_TOKEN", "test-token")


@pytest.fixture(autouse=True)
def _reset_all_state():
    """Reset all global state between tests."""
    from redhat_api_mcp import tools
    tools.set_client(None)
    tools._public_http = None
    tools._pyxis_bundle_cache.clear()
    tools._pyxis_packages_cache = None
    yield
    tools.set_client(None)
    tools._public_http = None
    tools._pyxis_bundle_cache.clear()
    tools._pyxis_packages_cache = None
