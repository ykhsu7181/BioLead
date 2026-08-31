"""Fixed sender profile loading for human-review email drafts."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_SENDER_PROFILE_PATH = Path("data/config/sender_profile.json")
SENDER_INTRO_STYLE_I_LEAD = "i_lead"
SENDER_INTRO_STYLE_ORGANIZATION_REPRESENTATIVE = "organization_representative"
_SUPPORTED_SENDER_INTRO_STYLES = {
    SENDER_INTRO_STYLE_I_LEAD,
    SENDER_INTRO_STYLE_ORGANIZATION_REPRESENTATIVE,
}


@dataclass(frozen=True)
class SenderProfile:
    """Non-secret sender identity used in generated outreach drafts."""

    profile_version: str
    sender_name: str
    sender_title: str
    sender_organization: str
    sender_email: str | None = None
    signature: str | None = None
    sender_intro_style: str = SENDER_INTRO_STYLE_ORGANIZATION_REPRESENTATIVE
    source_path: str | None = None


def load_sender_profile(
    path: Path | str | None = None,
) -> SenderProfile:
    """Load a fixed sender profile from JSON.

    The profile must not contain SMTP passwords, API keys, or authorization codes.
    """

    source_path = Path(
        path or os.getenv("SENDER_PROFILE_PATH") or DEFAULT_SENDER_PROFILE_PATH
    )
    if not source_path.exists():
        raise FileNotFoundError(f"sender profile not found: {source_path}")

    with source_path.open("r", encoding="utf-8") as profile_file:
        payload = json.load(profile_file)
    if not isinstance(payload, dict):
        raise ValueError("sender profile must be a JSON object")

    sender_intro_style = (
        _clean(payload.get("sender_intro_style"))
        or SENDER_INTRO_STYLE_ORGANIZATION_REPRESENTATIVE
    )
    if sender_intro_style not in _SUPPORTED_SENDER_INTRO_STYLES:
        raise ValueError(
            "sender_intro_style must be one of: "
            f"{', '.join(sorted(_SUPPORTED_SENDER_INTRO_STYLES))}"
        )

    return SenderProfile(
        profile_version=_clean(payload.get("profile_version")) or "unknown",
        sender_name=_required(payload, "sender_name"),
        sender_title=_required(payload, "sender_title"),
        sender_organization=_required(payload, "sender_organization"),
        sender_email=_clean(payload.get("sender_email")),
        signature=_clean(payload.get("signature")),
        sender_intro_style=sender_intro_style,
        source_path=str(source_path),
    )


def sender_profile_to_dict(profile: SenderProfile) -> dict[str, Any]:
    """Convert a sender profile to evidence-safe metadata."""

    return {
        "profile_version": profile.profile_version,
        "sender_name": profile.sender_name,
        "sender_title": profile.sender_title,
        "sender_organization": profile.sender_organization,
        "sender_email": profile.sender_email,
        "signature": profile.signature,
        "sender_intro_style": profile.sender_intro_style,
        "source_path": profile.source_path,
    }


def _required(payload: dict[str, Any], field_name: str) -> str:
    value = _clean(payload.get(field_name))
    if not value:
        raise ValueError(f"{field_name} is required in sender profile")
    return value


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
