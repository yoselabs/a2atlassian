"""Shape validation tests for watcher extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.watchers import _extract_watcher


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


class TestExtractWatcher:
    def test_handles_real_shape(self, real_watchers):
        watchers = real_watchers["watchers"]
        for watcher in watchers:
            result = _extract_watcher(watcher)
            _assert_flat(result)

    def test_expected_keys(self, real_watchers):
        watchers = real_watchers["watchers"]
        result = _extract_watcher(watchers[0])
        assert set(result.keys()) == {
            "account_id",
            "display_name",
        }
