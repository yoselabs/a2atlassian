"""Shape validation tests for comment extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.comments import _extract_comment


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


class TestExtractComment:
    def test_handles_real_shape(self, real_comments):
        comments = real_comments["comments"]
        for comment in comments:
            result = _extract_comment(comment)
            _assert_flat(result)

    def test_expected_keys(self, real_comments):
        comments = real_comments["comments"]
        result = _extract_comment(comments[0])
        assert set(result.keys()) == {
            "id",
            "author",
            "updated_by",
            "body",
            "created",
            "updated",
        }
