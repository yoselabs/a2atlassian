"""Shape validation tests for link type extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.links import _extract_link_type


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


class TestExtractLinkType:
    def test_handles_real_shape(self, real_link_types):
        link_types = real_link_types.get("issueLinkTypes") or real_link_types.get("items", [])
        for lt in link_types:
            result = _extract_link_type(lt)
            _assert_flat(result)

    def test_expected_keys(self, real_link_types):
        link_types = real_link_types.get("issueLinkTypes") or real_link_types.get("items", [])
        result = _extract_link_type(link_types[0])
        assert set(result.keys()) == {
            "id",
            "name",
            "inward",
            "outward",
        }
