"""Shape validation tests for worklog extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.worklogs import _extract_worklog


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


WORKLOG_KEYS = {
    "id",
    "author",
    "time_spent",
    "started",
    "comment",
}


class TestExtractWorklog:
    def test_handles_real_shape(self, real_worklogs):
        worklogs = real_worklogs["worklogs"]
        for worklog in worklogs:
            result = _extract_worklog(worklog)
            _assert_flat(result)

    def test_expected_keys(self, real_worklogs):
        worklogs = real_worklogs["worklogs"]
        result = _extract_worklog(worklogs[0])
        assert set(result.keys()) == WORKLOG_KEYS

    def test_rich_worklogs(self, real_worklogs_rich):
        """Worklogs from rich fixture should extract cleanly (handles null/ADF comments)."""
        worklogs = real_worklogs_rich["worklogs"]
        assert len(worklogs) >= 1
        for worklog in worklogs:
            result = _extract_worklog(worklog)
            _assert_flat(result)
            assert set(result.keys()) == WORKLOG_KEYS
            assert isinstance(result["comment"], str)
