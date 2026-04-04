"""Tests for the MCP server tool registrations and argument parsing."""

from __future__ import annotations

import pytest

from a2atlassian.mcp_server import _parse_register_args, _parse_scope_args


class TestParseRegisterArgs:
    def test_single_register(self) -> None:
        args = ["--register", "myproject", "https://p.atlassian.net", "e@m.com", "tok123"]
        result = _parse_register_args(args)
        assert len(result) == 1
        assert result[0].project == "myproject"
        assert result[0].url == "https://p.atlassian.net"
        assert result[0].email == "e@m.com"
        assert result[0].token == "tok123"
        assert result[0].read_only is True

    def test_multiple_register(self) -> None:
        args = [
            "--register",
            "a",
            "https://a.atlassian.net",
            "a@m.com",
            "tok_a",
            "--register",
            "b",
            "https://b.atlassian.net",
            "b@m.com",
            "tok_b",
        ]
        result = _parse_register_args(args)
        assert len(result) == 2
        assert result[0].project == "a"
        assert result[1].project == "b"

    def test_register_with_rw(self) -> None:
        args = ["--register", "myproject", "https://p.atlassian.net", "e@m.com", "tok123", "--rw"]
        result = _parse_register_args(args)
        assert result[0].read_only is False

    def test_empty_args(self) -> None:
        assert _parse_register_args([]) == []

    def test_insufficient_args_after_register(self) -> None:
        args = ["--register", "myproject", "https://p.atlassian.net"]
        with pytest.raises(ValueError, match="4 arguments"):
            _parse_register_args(args)


class TestParseScopeArgs:
    def test_single_scope(self) -> None:
        args = ["--scope", "myproject"]
        result = _parse_scope_args(args)
        assert result == ["myproject"]

    def test_multiple_scopes(self) -> None:
        args = ["--scope", "myproject", "--scope", "secondary"]
        result = _parse_scope_args(args)
        assert result == ["myproject", "secondary"]

    def test_no_scope(self) -> None:
        assert _parse_scope_args([]) == []

    def test_mixed_args(self) -> None:
        args = ["--scope", "myproject", "--register", "b", "u", "e", "t"]
        result = _parse_scope_args(args)
        assert result == ["myproject"]
