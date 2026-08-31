from scholarlead_agent.services.email_reviewer_workspace import (
    ABSTRACT_PREVIEW_LIMIT,
    build_email_reviewer_workspace,
)


def test_reviewer_workspace_projects_evidence_quality_and_versions() -> None:
    workspace = build_email_reviewer_workspace(
        {
            "draft_id": "draft-1",
            "draft_status": "review_pending",
            "can_send": False,
            "warnings": ["missing_verified_email"],
            "evidence": {
                "recent_publication_title": "Single-cell RNA sequencing in cancer",
                "abstract": "A" * (ABSTRACT_PREVIEW_LIMIT + 10),
                "matched_keywords": ["single-cell", "cancer"],
                "pmid": "1",
                "draft_mode": "capability_grounded",
                "email_prompt_version": "academic_cold_email_v2",
                "sender_profile": {"profile_version": "sender-v1"},
                "capability_match": {
                    "status": "partial_match",
                    "capability_match_id": "match-1",
                    "profile_version": "capabilities-v1",
                    "matcher_version": "matcher-v1",
                    "candidate_capabilities": [{"capability_id": "single_cell"}],
                },
                "quality_report": {"status": "warning", "warnings": ["generic_praise_detected"]},
            },
        }
    )

    assert workspace["paper_evidence"]["title"] == "Single-cell RNA sequencing in cancer"
    assert workspace["paper_evidence"]["abstract_preview"].endswith("...")
    assert workspace["capability_match"]["items"][0]["capability_id"] == "single_cell"
    assert workspace["quality_report"]["status"] == "warning"
    assert workspace["versions"]["prompt_version"] == "academic_cold_email_v2"
    assert workspace["warnings"] == ["missing_verified_email"]
