"""Shared test fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from a2atlassian.connections import ConnectionInfo


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
        project="testproj",
        url="https://testproj.atlassian.net",
        email="test@example.com",
        token="test-token-123",
        read_only=True,
    )
