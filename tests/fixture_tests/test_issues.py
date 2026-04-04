"""Shape validation tests for issue extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.issues import _extract_issue_detail, _extract_issue_summary


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


class TestExtractIssueDetail:
    def test_handles_real_shape(self, real_issue):
        result = _extract_issue_detail(real_issue)
        _assert_flat(result)

    def test_expected_keys(self, real_issue):
        result = _extract_issue_detail(real_issue)
        assert set(result.keys()) == {
            "key",
            "summary",
            "status",
            "status_category",
            "assignee",
            "reporter",
            "priority",
            "type",
            "parent",
            "labels",
            "components",
            "fix_versions",
            "description",
            "created",
            "updated",
        }


class TestExtractIssueSummary:
    def test_handles_real_shape(self, real_search):
        issues = real_search["issues"]
        for issue in issues:
            result = _extract_issue_summary(issue)
            _assert_flat(result)

    def test_expected_keys(self, real_search):
        issues = real_search["issues"]
        result = _extract_issue_summary(issues[0])
        assert set(result.keys()) == {
            "key",
            "summary",
            "status",
            "assignee",
            "priority",
            "type",
            "parent",
            "updated",
        }
