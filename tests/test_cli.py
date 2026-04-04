"""Tests for the CLI frontend."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest
from click.testing import CliRunner

from a2atlassian.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestCli:
    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "a2atlassian" in result.output

    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestLogin:
    def test_login_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["login", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output or "-p" in result.output

    @patch("a2atlassian.cli.AtlassianClient")
    def test_login_success(self, mock_client_cls, runner: CliRunner, tmp_path: Path) -> None:
        mock_instance = mock_client_cls.return_value
        mock_instance.validate = AsyncMock(return_value={"displayName": "Alice"})

        with patch("a2atlassian.cli._store") as mock_store_fn:
            store = mock_store_fn.return_value
            store.save.return_value = tmp_path / "test.toml"
            result = runner.invoke(
                cli,
                [
                    "login",
                    "-p",
                    "test",
                    "--url",
                    "https://test.atlassian.net",
                    "--email",
                    "t@t.com",
                    "--token",
                    "tok123",
                ],
            )

        assert result.exit_code == 0
        assert "saved" in result.output.lower() or "Alice" in result.output


class TestLogout:
    def test_logout_success(self, runner: CliRunner) -> None:
        with patch("a2atlassian.cli._store"):
            result = runner.invoke(cli, ["logout", "-p", "test"])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()


class TestConnections:
    def test_list_empty(self, runner: CliRunner) -> None:
        with patch("a2atlassian.cli._store") as mock_store_fn:
            mock_store_fn.return_value.list_connections.return_value = []
            result = runner.invoke(cli, ["connections"])
        assert result.exit_code == 0
        assert "no connections" in result.output.lower()
