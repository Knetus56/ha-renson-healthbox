"""Shared fixtures for the Healthbox integration tests."""
import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make custom_components/healthbox loadable as a real integration in tests."""
    yield
