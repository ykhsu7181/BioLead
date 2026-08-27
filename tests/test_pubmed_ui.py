from dataclasses import replace

from scholarlead_agent.pubmed_models import PubMedAuthor, PubMedLead, PubMedPaper
from scholarlead_agent.ai.email_drafts import EmailDraftInput, build_email_draft
from scholarlead_agent.email_review import EmailReviewDecision, apply_email_review_decision
from scholarlead_agent.email_sending import email_send_result_to_dict
from scholarlead_agent.email_smtp import send_reviewed_test_email
from scholarlead_agent.config import AppConfig
from scholarlead_agent.database import fetch_one, initialize_database
from scholarlead_agent.ui.streamlit_app import (
    build_data_source_rows,
    build_summary_metrics,
    build_workflow_step_rows,
    extract_run_report_paths,
    extract_tool_names,
    extract_tool_sources,
    filter_lead_rows,
    funding_rows_from_agent_messages,
    get_filter_options,
    lead_detail_evidence_rows,
    lead_detail_summary_rows,
    lead_manual_review_reason,
    leads_to_table_rows,
    normalize_language,
    official_score_rows_from_leads,
    _persist_email_send_result,
    organization_rows_from_leads,
    papers_to_table_rows,
    researcher_rows_from_leads,
    table_label,
    translate,
)


def make_paper() -> PubMedPaper:
    author = PubMedAuthor(
        full_name="Alice Smith",
        last_name="Smith",
        fore_name="Alice",
        initials="AS",
        author_position=1,
        is_last_author=True,
        affiliations=["Example University, Boston, MA, USA"],
    )
    return PubMedPaper(
        source="pubmed",
        pmid="12345678",
        doi="10.1000/example",
        title="Single cell RNA sequencing in cancer",
        abstract="Abstract text.",
        journal="Example Journal",
        publication_date="2024-01-01",
        publication_year=2024,
        article_types=["Journal Article"],
        mesh_terms=["Neoplasms"],
        keywords=["single cell"],
        authors=[author],
        affiliations=author.affiliations,
        source_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        raw_record_path="data/raw/pubmed/example_efetch.xml",
    )


def make_lead(
    *,
    lead_id: str,
    country: str,
    priority: str,
    email_status: str,
) -> PubMedLead:
    verified_email = (
        "alice.smith@example.edu"
        if email_status == "verified_from_pubmed_affiliation"
        else None
    )
    return PubMedLead(
        lead_id=lead_id,
        pi_full_name="Alice Smith",
        verified_email=verified_email,
        email_status=email_status,
        email_source_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high" if verified_email else "missing",
        institution="Example University",
        country=country,
        country_confidence="high" if country != "unknown" else "unknown",
        recent_publication_title="Single cell RNA sequencing in cancer",
        abstract="Abstract text.",
        journal="Example Journal",
        publication_year=2024,
        pmid="12345678",
        doi="10.1000/example",
        author_role="email_author" if verified_email else "candidate_pi_last_author",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/12345678/"],
        data_quality="email_evidence_available" if verified_email else "missing_email_candidate",
        manual_review_required=not bool(verified_email),
        notes="Test lead.",
        country_source="affiliation_text" if country != "unknown" else "unknown",
        raw_affiliation="Example University, Boston, MA, USA",
        matched_keywords=["single cell"],
        target_service_type="scRNA-seq",
        topic_match_score=80,
        publication_recency_score=100,
        email_contactability_score=100 if verified_email else 0,
        lead_score=90 if priority == "high" else 40,
        priority=priority,
        score_explanation="PubMed-only temporary score.",
    )


def test_build_summary_metrics_orders_core_counts() -> None:
    metrics = build_summary_metrics(
        {
            "status": "success",
            "pmid_count": 2,
            "paper_count": 2,
            "lead_count": 1,
            "leads_with_verified_email_count": 1,
            "missing_email_count": 0,
            "started_at": "2026-08-19T10:00:00",
            "finished_at": "2026-08-19T10:00:01",
        }
    )

    assert metrics[:6] == [
        ("Status", "success"),
        ("PMIDs", 2),
        ("Papers", 2),
        ("Leads", 1),
        ("Verified email leads", 1),
        ("Missing email", 0),
    ]


def test_language_helpers_support_chinese_and_english_defaults() -> None:
    assert normalize_language("中文") == "zh"
    assert normalize_language("English") == "en"
    assert translate("run_pubmed_search", "zh") == "运行 PubMed 检索"
    assert translate("run_pubmed_search", "en") == "Run PubMed search"
    assert table_label("Country", "zh") == "国家"
    assert table_label("Country", "en") == "Country"


def test_build_summary_metrics_supports_chinese_labels() -> None:
    metrics = build_summary_metrics(
        {
            "status": "success",
            "pmid_count": 2,
            "paper_count": 2,
            "lead_count": 1,
            "leads_with_verified_email_count": 1,
            "missing_email_count": 0,
        },
        language="zh",
    )

    assert metrics[:6] == [
        ("状态", "success"),
        ("PMID 数", 2),
        ("论文数", 2),
        ("线索数", 1),
        ("有验证邮箱的线索", 1),
        ("缺失邮箱", 0),
    ]


def test_build_workflow_step_rows_reflects_processed_export() -> None:
    rows = build_workflow_step_rows(
        {
            "status": "success",
            "processed_files": {"papers_csv": "papers.csv"},
        }
    )

    assert [row["Step"] for row in rows] == [
        "Input validation",
        "PubMed ESearch",
        "PubMed EFetch",
        "Paper parsing",
        "Lead generation",
        "Export",
    ]
    assert {row["Status"] for row in rows} == {"done"}


def test_build_workflow_step_rows_supports_chinese_labels() -> None:
    rows = build_workflow_step_rows(
        {
            "status": "success",
            "processed_files": {"papers_csv": "papers.csv"},
        },
        language="zh",
    )

    assert rows[0]["步骤"] == "输入验证"
    assert rows[0]["状态"] == "完成"
    assert rows[-1]["证据"] == "JSON / CSV / 运行报告"


def test_build_data_source_rows_marks_agent_sources() -> None:
    messages = [
        {
            "role": "tool",
            "name": "search_funding",
            "content": (
                '{"success": true, "source": "nih_reporter", '
                '"data": {"source": "nih_reporter", "queried_sources": ["nih_reporter"]}}'
            ),
        }
    ]

    rows = build_data_source_rows({}, agent_messages=messages)
    by_source = {row["Source"]: row for row in rows}

    assert by_source["PubMed"]["Status"] == "used"
    assert by_source["NIH RePORTER"]["Status"] == "used"
    assert by_source["Crossref"]["Status"] == "available via Agent"


def test_build_data_source_rows_supports_chinese_labels() -> None:
    rows = build_data_source_rows({}, language="zh")
    by_source = {row["数据源"]: row for row in rows}

    assert by_source["PubMed"]["状态"] == "已使用"
    assert by_source["OpenAlex"]["状态"] == "Agent 可用"


def test_papers_to_table_rows_contains_required_display_fields() -> None:
    rows = papers_to_table_rows([make_paper()])

    assert rows == [
        {
            "PMID": "12345678",
            "Title": "Single cell RNA sequencing in cancer",
            "Journal": "Example Journal",
            "Publication Year": 2024,
            "DOI": "10.1000/example",
            "Authors": "Alice Smith",
            "Source URL": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
        }
    ]


def test_leads_to_table_rows_and_filters_support_stage18_view() -> None:
    rows = leads_to_table_rows(
        [
            make_lead(
                lead_id="lead-1",
                country="United States",
                priority="high",
                email_status="verified_from_pubmed_affiliation",
            ),
            make_lead(
                lead_id="lead-2",
                country="unknown",
                priority="low",
                email_status="missing",
            ),
        ]
    )

    assert rows[0]["PI / Candidate"] == "Alice Smith"
    assert rows[0]["Verified Email"] == "alice.smith@example.edu"
    assert rows[1]["Verified Email"] == "missing"
    assert get_filter_options(rows, "Priority") == ["All", "high", "low"]

    filtered = filter_lead_rows(
        rows,
        country="United States",
        priority="high",
        email_status="verified_from_pubmed_affiliation",
    )

    assert len(filtered) == 1
    assert filtered[0]["Lead ID"] == "lead-1"


def test_leads_to_table_rows_and_filters_support_chinese_labels() -> None:
    rows = leads_to_table_rows(
        [
            make_lead(
                lead_id="lead-1",
                country="United States",
                priority="high",
                email_status="verified_from_pubmed_affiliation",
            ),
            make_lead(
                lead_id="lead-2",
                country="unknown",
                priority="low",
                email_status="missing",
            ),
        ],
        language="zh",
    )

    assert rows[0]["PI / 候选人"] == "Alice Smith"
    assert rows[0]["验证邮箱"] == "alice.smith@example.edu"
    assert get_filter_options(rows, "优先级", language="zh") == ["全部", "high", "low"]

    filtered = filter_lead_rows(
        rows,
        country="United States",
        priority="high",
        email_status="verified_from_pubmed_affiliation",
        language="zh",
    )

    assert len(filtered) == 1
    assert filtered[0]["线索 ID"] == "lead-1"
    assert filter_lead_rows(
        rows,
        country="全部",
        priority="全部",
        email_status="全部",
        language="zh",
    ) == rows


def test_filter_lead_rows_all_keeps_rows() -> None:
    rows = leads_to_table_rows(
        [
            make_lead(
                lead_id="lead-1",
                country="United States",
                priority="high",
                email_status="verified_from_pubmed_affiliation",
            )
        ]
    )

    assert filter_lead_rows(
        rows,
        country="All",
        priority="All",
        email_status="All",
    ) == rows


def test_lead_detail_summary_rows_show_core_customer_fields() -> None:
    lead = make_lead(
        lead_id="lead-1",
        country="United States",
        priority="high",
        email_status="verified_from_pubmed_affiliation",
    )

    rows = lead_detail_summary_rows(lead)
    values_by_field = {row["Field"]: row["Value"] for row in rows}

    assert values_by_field["PI / Candidate"] == "Alice Smith"
    assert values_by_field["Verified Email"] == "alice.smith@example.edu"
    assert values_by_field["Institution"] == "Example University"
    assert values_by_field["Country"] == "United States"
    assert values_by_field["Recent Paper"] == "Single cell RNA sequencing in cancer"
    assert values_by_field["Matched Keywords"] == "single cell"
    assert values_by_field["Manual Review Reason"] == "not_required"


def test_lead_detail_evidence_rows_keep_sources_and_explanations() -> None:
    lead = make_lead(
        lead_id="lead-1",
        country="United States",
        priority="high",
        email_status="verified_from_pubmed_affiliation",
    )

    rows = lead_detail_evidence_rows(lead)
    rows_by_field = {row["Field"]: row for row in rows}

    assert rows_by_field["Verified Email"]["Source"] == "pubmed_affiliation"
    assert rows_by_field["Verified Email"]["Confidence"] == "high"
    assert rows_by_field["Verified Email"]["Evidence"] == lead.email_source_url
    assert rows_by_field["Institution"]["Evidence"] == lead.raw_affiliation
    assert rows_by_field["Country"]["Source"] == "affiliation_text"
    assert rows_by_field["Temporary Score"]["Evidence"] == "PubMed-only temporary score."
    assert "Candidate lead only" in rows_by_field["PI / Candidate"]["Evidence"]


def test_lead_detail_evidence_rows_mark_uncertain_fields() -> None:
    lead = make_lead(
        lead_id="lead-2",
        country="unknown",
        priority="low",
        email_status="missing",
    )
    lead = replace(
        lead,
        institution=None,
        raw_affiliation=None,
        source_links=[],
        matched_keywords=[],
        target_service_type=None,
    )

    rows = lead_detail_evidence_rows(lead)
    rows_by_field = {row["Field"]: row for row in rows}

    assert lead_manual_review_reason(lead) == "missing_email_candidate"
    assert rows_by_field["Verified Email"]["Value"] == "missing"
    assert rows_by_field["Institution"]["Value"] == "unknown"
    assert rows_by_field["Institution"]["Evidence"] == "unknown"
    assert rows_by_field["Country"]["Value"] == "unknown"
    assert rows_by_field["Matched Keywords"]["Value"] == "unknown"
    assert rows_by_field["Data Source Links"]["Confidence"] == "unknown"
    assert rows_by_field["Manual Review Required"]["Evidence"] == "missing_email_candidate"


def test_agent_helpers_are_available_for_streamlit_area() -> None:
    messages = [
        {
            "role": "tool",
            "name": "search_pubmed",
            "content": (
                '{"success": true, "source": "pubmed", '
                '"data": {"run_report_path": "report.json"}}'
            ),
        }
    ]

    assert extract_tool_names(messages) == ["search_pubmed"]
    assert extract_tool_sources(messages) == ["pubmed"]
    assert extract_run_report_paths(messages) == ["report.json"]


def test_researcher_and_organization_rows_are_display_ready() -> None:
    leads = [
        make_lead(
            lead_id="lead-1",
            country="United States",
            priority="high",
            email_status="verified_from_pubmed_affiliation",
        )
    ]

    researchers = researcher_rows_from_leads(leads)
    organizations = organization_rows_from_leads(leads)

    assert researchers[0]["Name"] == "Alice Smith"
    assert researchers[0]["Emails"] == "alice.smith@example.edu"
    assert organizations[0]["Name"] == "Example University"
    assert organizations[0]["Country"] == "United States"


def test_official_score_rows_show_missing_evidence_in_ui() -> None:
    rows = official_score_rows_from_leads(
        [
            make_lead(
                lead_id="lead-1",
                country="United States",
                priority="high",
                email_status="verified_from_pubmed_affiliation",
            )
        ]
    )

    assert rows[0]["Official Total Score"] == "missing evidence"
    assert rows[0]["Priority"] == "unscored"
    assert "funding_activity" in rows[0]["Missing Dimensions"]
    assert rows[0]["Research Direction Score"] == 80


def test_funding_rows_can_be_extracted_from_agent_messages() -> None:
    messages = [
        {
            "role": "tool",
            "name": "search_funding",
            "content": json_string(
                {
                    "success": True,
                    "source": "nih_reporter",
                    "data": {
                        "source": "nih_reporter",
                        "funding_records": [
                            {
                                "grant_id": "R01CA123456",
                                "agency": "NCI",
                                "project_title": "Cancer imaging",
                                "pi_name": "Alice Smith",
                                "institution": "Example University",
                                "fiscal_year": 2026,
                                "amount": 250000.0,
                                "source_url": "https://reporter.nih.gov/project-details/1",
                            }
                        ],
                    },
                }
            ),
        }
    ]

    rows = funding_rows_from_agent_messages(messages)

    assert rows == [
        {
            "Grant ID": "R01CA123456",
            "Agency": "NCI",
            "Project Title": "Cancer imaging",
            "PI Name": "Alice Smith",
            "Institution": "Example University",
            "Fiscal Year": 2026,
            "Amount": 250000.0,
            "Source URL": "https://reporter.nih.gov/project-details/1",
        }
    ]


def json_string(payload: dict) -> str:
    import json

    return json.dumps(payload)


def test_persist_email_send_result_inserts_required_foreign_key_rows(tmp_path) -> None:
    lead = make_lead(
        lead_id="lead-1",
        country="United States",
        priority="high",
        email_status="verified_from_pubmed_affiliation",
    )
    draft = build_email_draft(
        evidence=EmailDraftInput(
            lead_id=lead.lead_id,
            pi_full_name=lead.pi_full_name,
            recent_publication_title=lead.recent_publication_title,
            source_url=lead.email_source_url,
            target_service_type=lead.target_service_type,
            verified_email=lead.verified_email,
            email_status=lead.email_status,
        ),
        subject="Test subject",
        body="Dear Dr. Smith,\n\nTest body.",
        model_name="fake-model",
        generated_at="2026-08-25T10:00:00",
    )
    reviewed = apply_email_review_decision(
        draft,
        EmailReviewDecision(
            reviewer="Reviewer",
            decision="approve",
            reviewed_at="2026-08-25T10:05:00",
        ),
    )
    result = send_reviewed_test_email(
        reviewed,
        actor="Reviewer",
        config=AppConfig(
            email_provider="smtp",
            email_send_enabled=False,
            email_sender="agent_test@yeah.net",
            email_test_recipient="tester@qq.com",
            email_allowed_recipients=("tester@qq.com",),
            email_daily_limit=5,
            smtp_host="smtp.yeah.net",
            smtp_username="agent_test@yeah.net",
            smtp_password="authorization-code",
        ),
        send_id="send-1",
    )

    _persist_email_send_result(
        database_path=tmp_path / "scholarlead.sqlite",
        lead=lead,
        draft_data=reviewed,
        draft_id="draft-1",
        result_data=email_send_result_to_dict(result),
    )

    with initialize_database(tmp_path / "scholarlead.sqlite") as connection:
        send_log = fetch_one(
            connection,
            "SELECT * FROM email_send_logs WHERE send_id = ?",
            ("send-1",),
        )
        stored_lead = fetch_one(
            connection,
            "SELECT * FROM leads WHERE lead_id = ?",
            (lead.lead_id,),
        )
        stored_draft = fetch_one(
            connection,
            "SELECT * FROM email_drafts WHERE draft_id = ?",
            ("draft-1",),
        )

    assert send_log is not None
    assert send_log["status"] == "blocked"
    assert stored_lead is not None
    assert stored_draft is not None
