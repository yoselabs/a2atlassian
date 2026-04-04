"""Shape validation tests for board extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.boards import _extract_board


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


class TestExtractBoard:
    def test_handles_real_shape(self, real_boards):
        boards = real_boards["values"]
        for board in boards:
            result = _extract_board(board)
            _assert_flat(result)

    def test_expected_keys(self, real_boards):
        boards = real_boards["values"]
        result = _extract_board(boards[0])
        assert set(result.keys()) == {
            "id",
            "name",
            "type",
            "project_key",
        }
