"""Shape validation tests for issue extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.issues import _extract_issue_detail, _extract_issue_summary


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


DETAIL_KEYS = {
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

SUMMARY_KEYS = {
    "key",
    "summary",
    "status",
    "assignee",
    "priority",
    "type",
    "parent",
    "updated",
}


class TestExtractIssueDetail:
    def test_handles_real_shape(self, real_issue):
        result = _extract_issue_detail(real_issue)
        _assert_flat(result)

    def test_expected_keys(self, real_issue):
        result = _extract_issue_detail(real_issue)
        assert set(result.keys()) == DETAIL_KEYS

    def test_full_issue_has_populated_fields(self, real_issue_full):
        result = _extract_issue_detail(real_issue_full)
        _assert_flat(result)
        assert set(result.keys()) == DETAIL_KEYS
        # Full issue must have non-empty labels, components, fix_versions
        assert result["labels"], "Expected non-empty labels"
        assert result["components"], "Expected non-empty components"
        assert result["fix_versions"], "Expected non-empty fix_versions"
        # They should be comma-joined strings
        assert "," in result["labels"]
        assert "," in result["components"]
        assert "," in result["fix_versions"]

    def test_minimal_issue_handles_nulls(self, real_issue_minimal):
        result = _extract_issue_detail(real_issue_minimal)
        _assert_flat(result)
        assert set(result.keys()) == DETAIL_KEYS
        # Minimal issue has null assignee — should be empty string
        assert result["assignee"] == ""
        # Empty collections should be empty strings
        assert result["labels"] == ""
        assert result["components"] == ""
        assert result["fix_versions"] == ""

    def test_epic_type(self, real_issue_epic):
        result = _extract_issue_detail(real_issue_epic)
        _assert_flat(result)
        assert set(result.keys()) == DETAIL_KEYS
        assert result["type"] == "Epic"

    def test_subtask_type_with_parent(self, real_issue_subtask):
        result = _extract_issue_detail(real_issue_subtask)
        _assert_flat(result)
        assert set(result.keys()) == DETAIL_KEYS
        assert result["type"] == "Sub-task"
        assert result["parent"], "Sub-task should have a parent key"

    def test_done_status(self, real_issue_done):
        result = _extract_issue_detail(real_issue_done)
        _assert_flat(result)
        assert set(result.keys()) == DETAIL_KEYS
        assert result["status"] == "Done"
        assert result["status_category"] == "Done"


class TestExtractIssueSummary:
    def test_handles_real_shape(self, real_search):
        issues = real_search["issues"]
        for issue in issues:
            result = _extract_issue_summary(issue)
            _assert_flat(result)

    def test_expected_keys(self, real_search):
        issues = real_search["issues"]
        result = _extract_issue_summary(issues[0])
        assert set(result.keys()) == SUMMARY_KEYS

    def test_assigned_search_all_have_assignees(self, real_search_assigned):
        for issue in real_search_assigned["issues"]:
            result = _extract_issue_summary(issue)
            _assert_flat(result)
            assert set(result.keys()) == SUMMARY_KEYS
            assert result["assignee"], f"{result['key']} should have an assignee"

    def test_labels_search(self, real_search_labels):
        for issue in real_search_labels["issues"]:
            result = _extract_issue_summary(issue)
            _assert_flat(result)
            assert set(result.keys()) == SUMMARY_KEYS
