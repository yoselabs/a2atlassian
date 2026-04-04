"""Shape validation tests for transition extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.transitions import _extract_transition


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


class TestExtractTransition:
    def test_handles_real_shape(self, real_transitions):
        items = real_transitions["items"]
        for item in items:
            result = _extract_transition(item)
            _assert_flat(result)

    def test_expected_keys(self, real_transitions):
        items = real_transitions["items"]
        result = _extract_transition(items[0])
        assert set(result.keys()) == {
            "id",
            "name",
            "to_status",
        }
