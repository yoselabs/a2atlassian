"""Tests for error enrichment."""

from __future__ import annotations

from a2atlassian.errors import ErrorEnricher


class TestErrorEnricher:
    def setup_method(self) -> None:
        self.enricher = ErrorEnricher()

    def test_jql_field_suggestion(self) -> None:
        result = self.enricher.enrich("Field 'asignee' does not exist")
        assert "Did you mean: assignee" in result

    def test_assignee_account_id_hint(self) -> None:
        result = self.enricher.enrich("Cannot set assignee with 712020:abc123")
        assert "display name" in result

    def test_issue_type_conversion_hint(self) -> None:
        result = self.enricher.enrich("Cannot change issuetype: Bad Request")
        assert "Jira UI" in result

    def test_read_only_hint(self) -> None:
        result = self.enricher.enrich("Connection is read-only", {"project": "myproject"})
        assert "a2atlassian login -p myproject --read-only false" in result

    def test_field_suggestion_with_available(self) -> None:
        ctx = {"available_fields": ["Story Points", "Sprint", "Epic Link"]}
        result = self.enricher.enrich("Field 'story_point' does not exist", ctx)
        assert "Story Points" in result

    def test_no_enrichment_for_generic_error(self) -> None:
        result = self.enricher.enrich("Something went wrong")
        assert result == "Something went wrong"
