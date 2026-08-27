import json
from pathlib import Path

import pytest

from scholarlead_agent.sender_profile import (
    SenderProfile,
    load_sender_profile,
    sender_profile_to_dict,
)


def test_load_sender_profile_from_json(tmp_path: Path) -> None:
    profile_path = tmp_path / "sender_profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_version": "v1",
                "sender_name": "Alex Chen",
                "sender_title": "Research Partnership Manager",
                "sender_organization": "Example Bio",
                "sender_email": "alex@example.com",
                "signature": "Best regards,\nAlex",
            }
        ),
        encoding="utf-8",
    )

    profile = load_sender_profile(profile_path)

    assert profile.profile_version == "v1"
    assert profile.sender_name == "Alex Chen"
    assert profile.sender_title == "Research Partnership Manager"
    assert profile.sender_organization == "Example Bio"
    assert profile.sender_email == "alex@example.com"
    assert profile.source_path == str(profile_path)


def test_load_sender_profile_requires_sender_name(tmp_path: Path) -> None:
    profile_path = tmp_path / "sender_profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "sender_title": "Research Partnership Manager",
                "sender_organization": "Example Bio",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="sender_name is required"):
        load_sender_profile(profile_path)


def test_sender_profile_to_dict_is_evidence_safe() -> None:
    data = sender_profile_to_dict(
        SenderProfile(
            profile_version="v1",
            sender_name="Alex Chen",
            sender_title="Research Partnership Manager",
            sender_organization="Example Bio",
            sender_email="alex@example.com",
            signature="Best regards,\nAlex",
            source_path="sender_profile.json",
        )
    )

    assert data["sender_name"] == "Alex Chen"
    assert "password" not in json.dumps(data).lower()
