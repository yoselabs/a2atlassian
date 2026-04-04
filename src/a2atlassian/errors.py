"""Custom exceptions and error enrichment."""

from __future__ import annotations

from difflib import get_close_matches


class A2AtlassianError(Exception):
    """Base error for a2atlassian."""


class WriteAccessDeniedError(A2AtlassianError):
    """Raised when a write operation is attempted on a read-only connection."""


class RateLimitError(A2AtlassianError):
    """Raised when Atlassian returns 429 Too Many Requests."""


class ServerError(A2AtlassianError):
    """Raised on transient 5xx errors."""


class AuthenticationError(A2AtlassianError):
    """Raised on 401/403 responses."""


class ErrorEnricher:
    """Catches API errors and adds actionable context."""

    JQL_FIELDS: list[str] = [  # noqa: RUF012
        "assignee",
        "reporter",
        "creator",
        "status",
        "summary",
        "description",
        "priority",
        "issuetype",
        "project",
        "resolution",
        "created",
        "updated",
        "due",
        "labels",
        "component",
        "fixVersion",
        "sprint",
        "epic",
    ]

    def enrich(self, error_msg: str, context: dict | None = None) -> str:
        """Add actionable hints to an error message."""
        context = context or {}
        parts = [error_msg]

        if "field" in error_msg.lower() or "not exist" in error_msg.lower():
            parts.extend(self._suggest_field(error_msg, context))

        if "712020:" in error_msg or "assignee" in error_msg.lower():
            parts.extend(self._hint_assignee(error_msg))

        if "issuetype" in error_msg.lower() and ("bad request" in error_msg.lower() or "cannot" in error_msg.lower()):
            parts.append(
                'Hint: Issue type cannot be changed via API. Use Jira UI: open issue → "..." menu → "Convert to work item" → follow wizard.'
            )

        if "read-only" in error_msg.lower() or "read_only" in error_msg.lower():
            project = context.get("project", "<project>")
            parts.append(f"Run: a2atlassian login -p {project} --read-only false")

        return "\n".join(parts)

    def _suggest_field(self, error_msg: str, context: dict) -> list[str]:
        hints = []
        available = context.get("available_fields", [])
        field_names = [f["name"] if isinstance(f, dict) else str(f) for f in available]
        all_names = field_names or self.JQL_FIELDS

        for word in error_msg.split("'"):
            if len(word) > 1 and word.replace("_", "").isalpha():
                matches = get_close_matches(word, all_names, n=3, cutoff=0.4)
                if matches:
                    hints.append(f"Did you mean: {', '.join(matches)}?")
                    break

        if field_names:
            hints.append(f"Available fields: {', '.join(field_names[:20])}")
        return hints

    def _hint_assignee(self, error_msg: str) -> list[str]:
        if "712020:" in error_msg:
            return [
                "Hint: Use display name instead of account ID. "
                'Account IDs in "712020:" format are not supported. '
                'Pass the user\'s display name as a plain string (e.g., "Alice Smith").'
            ]
        return []
