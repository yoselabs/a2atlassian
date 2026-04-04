"""Tests for TOON and JSON output formatting."""

from __future__ import annotations

import json

from a2atlassian.formatter import FIELD_MAX_LENGTH, OperationResult, format_result


class TestOperationResult:
    def test_single_entity(self) -> None:
        result = OperationResult(
            name="get_issue",
            data={"key": "PROJ-1", "summary": "Test issue"},
            count=1,
            truncated=False,
            time_ms=50,
        )
        assert result.count == 1
        assert result.truncated is False

    def test_list_result(self) -> None:
        result = OperationResult(
            name="search",
            data=[
                {"key": "PROJ-1", "summary": "First"},
                {"key": "PROJ-2", "summary": "Second"},
            ],
            count=2,
            truncated=False,
            time_ms=120,
        )
        assert result.count == 2


class TestFormatJson:
    def test_single_entity(self) -> None:
        result = OperationResult(
            name="get_issue",
            data={"key": "PROJ-1", "summary": "Test"},
            count=1,
            truncated=False,
            time_ms=50,
        )
        output = format_result(result, fmt="json")
        parsed = json.loads(output)
        assert parsed["data"]["key"] == "PROJ-1"
        assert parsed["count"] == 1
        assert parsed["time_ms"] == 50
        assert parsed["truncated"] is False

    def test_list_result(self) -> None:
        result = OperationResult(
            name="search",
            data=[{"key": "PROJ-1"}, {"key": "PROJ-2"}],
            count=2,
            truncated=True,
            time_ms=200,
        )
        output = format_result(result, fmt="json")
        parsed = json.loads(output)
        assert len(parsed["data"]) == 2
        assert parsed["truncated"] is True

    def test_field_truncation(self) -> None:
        long_text = "x" * (FIELD_MAX_LENGTH + 500)
        result = OperationResult(
            name="get_issue",
            data={"key": "PROJ-1", "description": long_text},
            count=1,
            truncated=False,
            time_ms=10,
        )
        output = format_result(result, fmt="json")
        parsed = json.loads(output)
        desc = parsed["data"]["description"]
        assert len(desc) < len(long_text)
        assert desc.endswith("... [truncated]")


class TestFormatToon:
    def test_list_uses_toon(self) -> None:
        result = OperationResult(
            name="search",
            data=[
                {"key": "PROJ-1", "summary": "First"},
                {"key": "PROJ-2", "summary": "Second"},
            ],
            count=2,
            truncated=False,
            time_ms=100,
        )
        output = format_result(result, fmt="toon")
        assert isinstance(output, str)
        assert "PROJ-1" in output
        assert "PROJ-2" in output

    def test_single_entity_falls_back_to_json(self) -> None:
        result = OperationResult(
            name="get_issue",
            data={"key": "PROJ-1", "summary": "Test"},
            count=1,
            truncated=False,
            time_ms=50,
        )
        output = format_result(result, fmt="toon")
        parsed = json.loads(output)
        assert parsed["data"]["key"] == "PROJ-1"

    def test_metadata_present(self) -> None:
        result = OperationResult(
            name="search",
            data=[{"key": "PROJ-1"}],
            count=1,
            truncated=False,
            time_ms=75,
        )
        output = format_result(result, fmt="toon")
        assert "75" in output or "time_ms" in output
