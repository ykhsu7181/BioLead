"""Agent Tool wrapper for English email draft generation."""

from __future__ import annotations

from typing import Any, Protocol

from scholarlead_agent.agent.tool_types import ToolDefinition, ToolResult
from scholarlead_agent.ai.email_drafts import (
    EmailDraft,
    EmailDraftInput,
    email_draft_to_dict,
    validate_email_draft_input,
)
from scholarlead_agent.services.email_draft_service import (
    EmailDraftGenerationError,
    EmailDraftService,
)


GENERATE_EMAIL_DRAFT_TOOL_NAME = "generate_email_draft"

GENERATE_EMAIL_DRAFT_DESCRIPTION = (
    "Generate one personalized English email draft for human review from "
    "provided PubMed Lead evidence. This tool does not send email, does not "
    "approve email, and must not invent funding, emails, affiliations, or "
    "paper findings that are not present in the arguments."
)

GENERATE_EMAIL_DRAFT_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "lead_id",
        "pi_full_name",
        "recent_publication_title",
        "source_url",
        "target_service_type",
    ],
    "properties": {
        "lead_id": {"type": "string", "minLength": 1},
        "pi_full_name": {"type": "string", "minLength": 1},
        "recent_publication_title": {"type": "string", "minLength": 1},
        "source_url": {"type": "string", "minLength": 1},
        "target_service_type": {"type": "string", "minLength": 1},
        "abstract": {"type": "string"},
        "institution": {"type": "string"},
        "country": {"type": "string"},
        "verified_email": {"type": "string"},
        "email_status": {"type": "string"},
        "pmid": {"type": "string"},
        "doi": {"type": "string"},
        "matched_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Matched research keywords from the Lead evidence.",
        },
        "sender_name": {"type": "string"},
        "sender_title": {"type": "string"},
        "organization_name": {"type": "string"},
        "service_context": {"type": "string"},
        "matched_service_id": {"type": "string"},
        "matched_service_name": {"type": "string"},
        "service_match_score": {"type": "number"},
        "service_match_reason": {"type": "string"},
        "service_matched_terms": {
            "type": "array",
            "items": {"type": "string"},
        },
        "service_match_status": {"type": "string"},
        "service_catalog_version": {"type": "string"},
        "service_matcher_version": {"type": "string"},
        "sender_profile_version": {"type": "string"},
        "sender_email": {"type": "string"},
        "sender_signature": {"type": "string"},
    },
}


class EmailDraftServiceRunner(Protocol):
    """Protocol for services used by the email draft tool."""

    def generate(self, evidence: EmailDraftInput) -> EmailDraft:
        """Generate one email draft."""


def generate_email_draft(
    arguments: dict[str, Any],
    *,
    service: EmailDraftServiceRunner | None = None,
) -> ToolResult:
    """Generate one structured email draft from tool-call arguments."""

    try:
        evidence = _validate_tool_arguments(arguments)
    except ValueError as error:
        return ToolResult(
            success=False,
            source="email_draft",
            error_code="invalid_arguments",
            error_message=str(error),
        )

    try:
        draft = (service or EmailDraftService()).generate(evidence)
    except EmailDraftGenerationError as error:
        return ToolResult(
            success=False,
            source="email_draft",
            error_code="email_draft_generation_failed",
            error_message=str(error),
        )
    except Exception as error:
        return ToolResult(
            success=False,
            source="email_draft",
            error_code="tool_execution_error",
            error_message=str(error),
        )

    return ToolResult(
        success=True,
        source="email_draft",
        data=email_draft_to_dict(draft),
    )


GENERATE_EMAIL_DRAFT_TOOL = ToolDefinition(
    name=GENERATE_EMAIL_DRAFT_TOOL_NAME,
    description=GENERATE_EMAIL_DRAFT_DESCRIPTION,
    input_schema=GENERATE_EMAIL_DRAFT_INPUT_SCHEMA,
    effect="external",
    handler=generate_email_draft,
)


def _validate_tool_arguments(arguments: dict[str, Any]) -> EmailDraftInput:
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")

    unexpected_fields = set(arguments) - set(
        GENERATE_EMAIL_DRAFT_INPUT_SCHEMA["properties"]
    )
    if unexpected_fields:
        names = ", ".join(sorted(unexpected_fields))
        raise ValueError(f"unexpected argument(s): {names}")

    for field_name in GENERATE_EMAIL_DRAFT_INPUT_SCHEMA["required"]:
        if field_name not in arguments:
            raise ValueError(f"{field_name} is required")

    return validate_email_draft_input(
        EmailDraftInput(
            lead_id=_require_string(arguments["lead_id"], "lead_id"),
            pi_full_name=_require_string(arguments["pi_full_name"], "pi_full_name"),
            recent_publication_title=_require_string(
                arguments["recent_publication_title"],
                "recent_publication_title",
            ),
            source_url=_require_string(arguments["source_url"], "source_url"),
            target_service_type=_require_string(
                arguments["target_service_type"],
                "target_service_type",
            ),
            abstract=_optional_string(arguments.get("abstract"), "abstract"),
            institution=_optional_string(arguments.get("institution"), "institution"),
            country=_optional_string(arguments.get("country"), "country"),
            verified_email=_optional_string(
                arguments.get("verified_email"),
                "verified_email",
            ),
            email_status=_optional_string(arguments.get("email_status"), "email_status"),
            pmid=_optional_string(arguments.get("pmid"), "pmid"),
            doi=_optional_string(arguments.get("doi"), "doi"),
            matched_keywords=_split_keywords(arguments.get("matched_keywords")),
            sender_name=_optional_string(arguments.get("sender_name"), "sender_name"),
            sender_title=_optional_string(arguments.get("sender_title"), "sender_title"),
            organization_name=_optional_string(
                arguments.get("organization_name"),
                "organization_name",
            ),
            service_context=_optional_string(
                arguments.get("service_context"),
                "service_context",
            ),
            matched_service_id=_optional_string(
                arguments.get("matched_service_id"),
                "matched_service_id",
            ),
            matched_service_name=_optional_string(
                arguments.get("matched_service_name"),
                "matched_service_name",
            ),
            service_match_score=_optional_number(
                arguments.get("service_match_score"),
                "service_match_score",
            ),
            service_match_reason=_optional_string(
                arguments.get("service_match_reason"),
                "service_match_reason",
            ),
            service_matched_terms=_split_keywords(
                arguments.get("service_matched_terms")
            ),
            service_match_status=_optional_string(
                arguments.get("service_match_status"),
                "service_match_status",
            ),
            service_catalog_version=_optional_string(
                arguments.get("service_catalog_version"),
                "service_catalog_version",
            ),
            service_matcher_version=_optional_string(
                arguments.get("service_matcher_version"),
                "service_matcher_version",
            ),
            sender_profile_version=_optional_string(
                arguments.get("sender_profile_version"),
                "sender_profile_version",
            ),
            sender_email=_optional_string(arguments.get("sender_email"), "sender_email"),
            sender_signature=_optional_string(
                arguments.get("sender_signature"),
                "sender_signature",
            ),
        )
    )


def _split_keywords(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        keywords: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("matched_keywords must contain strings")
            cleaned = item.strip()
            if cleaned:
                keywords.append(cleaned)
        return keywords
    if not isinstance(value, str):
        raise ValueError("matched_keywords must be a string or array")
    return [item.strip() for item in value.split(",") if item.strip()]


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def _optional_number(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be a number")
    return float(value)
