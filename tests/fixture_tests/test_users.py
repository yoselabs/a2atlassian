"""Shape validation tests for user extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.users import _extract_user


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


class TestExtractUser:
    def test_handles_real_shape(self, real_user):
        result = _extract_user(real_user)
        _assert_flat(result)

    def test_expected_keys(self, real_user):
        result = _extract_user(real_user)
        assert set(result.keys()) == {
            "account_id",
            "display_name",
            "email",
            "active",
        }
