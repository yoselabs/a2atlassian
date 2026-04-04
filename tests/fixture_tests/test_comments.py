"""Shape validation tests for comment extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.comments import _extract_comment


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


COMMENT_KEYS = {
    "id",
    "author",
    "updated_by",
    "body",
    "created",
    "updated",
}


class TestExtractComment:
    def test_handles_real_shape(self, real_comments):
        comments = real_comments["comments"]
        for comment in comments:
            result = _extract_comment(comment)
            _assert_flat(result)

    def test_expected_keys(self, real_comments):
        comments = real_comments["comments"]
        result = _extract_comment(comments[0])
        assert set(result.keys()) == COMMENT_KEYS

    def test_rich_wiki_markup_comments(self, real_comments_rich):
        """Rich comments with wiki markup should extract cleanly as strings."""
        comments = real_comments_rich["comments"]
        assert len(comments) >= 1
        for comment in comments:
            result = _extract_comment(comment)
            _assert_flat(result)
            assert set(result.keys()) == COMMENT_KEYS
            assert isinstance(result["body"], str)
            assert result["body"], "Rich comment body should not be empty"
