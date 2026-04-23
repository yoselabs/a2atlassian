"""Shared test fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from a2atlassian.connections import ConnectionInfo


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--integration", action="store_true", default=False, help="Run integration tests against a real Jira instance")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption("--integration"):
        skip = pytest.mark.skip(reason="needs --integration flag")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Temporary config directory for connection tests."""
    config_dir = tmp_path / "connections"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_connection() -> ConnectionInfo:
    """A sample connection for testing."""
    return ConnectionInfo(
        connection="testproj",
        url="https://testproj.atlassian.net",
        email="test@example.com",
        token="test-token-123",
        read_only=True,
    )
