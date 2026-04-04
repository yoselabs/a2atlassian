"""Shape validation tests for field extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.fields import _extract_field, _extract_option


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


class TestExtractField:
    def test_handles_real_shape(self, real_fields):
        fields = real_fields["items"]
        for field in fields:
            result = _extract_field(field)
            _assert_flat(result)

    def test_expected_keys(self, real_fields):
        fields = real_fields["items"]
        result = _extract_field(fields[0])
        assert set(result.keys()) == {
            "id",
            "name",
            "custom",
            "schema_type",
        }


class TestExtractOption:
    def test_handles_real_shape(self, real_field_options):
        options = real_field_options["values"]
        for option in options:
            result = _extract_option(option)
            _assert_flat(result)

    def test_expected_keys(self, real_field_options):
        options = real_field_options["values"]
        result = _extract_option(options[0])
        assert set(result.keys()) == {
            "id",
            "value",
        }
