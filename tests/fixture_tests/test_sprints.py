"""Shape validation tests for sprint extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.issues import _extract_issue_summary
from a2atlassian.jira.sprints import _extract_sprint


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


class TestExtractSprint:
    def test_handles_real_shape(self, real_sprints):
        sprints = real_sprints["values"]
        for sprint in sprints:
            result = _extract_sprint(sprint)
            _assert_flat(result)

    def test_expected_keys(self, real_sprints):
        sprints = real_sprints["values"]
        result = _extract_sprint(sprints[0])
        assert set(result.keys()) == {
            "id",
            "name",
            "state",
            "start_date",
            "end_date",
        }


class TestExtractSprintIssueSummary:
    def test_handles_real_shape(self, real_sprint_issues):
        issues = real_sprint_issues["issues"]
        for issue in issues:
            result = _extract_issue_summary(issue)
            _assert_flat(result)

    def test_expected_keys(self, real_sprint_issues):
        issues = real_sprint_issues["issues"]
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
