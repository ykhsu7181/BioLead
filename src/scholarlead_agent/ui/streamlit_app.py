"""Streamlit UI for ScholarLead Agent.

The UI is intentionally thin. It validates user input, calls existing services
and tools, displays returned objects, and downloads files already written by the
storage layer. It does not send real email.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from scholarlead_agent.adapters.openai_compatible_chat import LLMAdapterError
from scholarlead_agent.agent.loop import AgentRunError
from scholarlead_agent.agent.runtime import (
    extract_run_report_paths,
    extract_tool_names,
    extract_tool_sources,
    run_agent_conversation,
)
from scholarlead_agent.ai.email_drafts import (
    email_draft_to_dict,
)
from scholarlead_agent.ai.usage import load_ai_usage_records, summarize_ai_usage
from scholarlead_agent.config import load_config
from scholarlead_agent.database import (
    fetch_one,
    initialize_database,
    insert_email_draft,
    insert_email_send_log,
    insert_pubmed_lead,
)
from scholarlead_agent.email_review import (
    EmailReviewDecision,
    append_email_audit_record,
    apply_email_review_decision,
    build_email_audit_record,
    email_audit_record_to_dict,
    evaluate_send_permission,
)
from scholarlead_agent.email_sending import email_send_result_to_dict
from scholarlead_agent.email_smtp import (
    build_test_send_preview,
    send_reviewed_test_email,
)
from scholarlead_agent.entity_resolution import resolve_pubmed_leads_to_entities
from scholarlead_agent.official_scoring import score_pubmed_lead_official_minimal
from scholarlead_agent.pubmed_models import (
    PUBMED_MAX_RESULTS_LIMIT,
    PubMedLead,
    PubMedPaper,
    validate_pubmed_search_inputs,
)
from scholarlead_agent.result_package import build_result_package_from_pubmed_result
from scholarlead_agent.services.email_draft_service import (
    EmailDraftGenerationError,
    EmailDraftService,
    build_auto_email_draft_input_from_lead,
)
from scholarlead_agent.services.pubmed_service import PubMedRunResult, run_pubmed_search


IMPLEMENTED_CAPABILITIES = [
    "PubMed ESearch / EFetch",
    "Raw data preservation",
    "Paper parsing and deduplication",
    "Public email evidence from PubMed affiliation text",
    "Lead generation and deduplication",
    "Basic institution and country recognition",
    "Keyword matching and PubMed-only temporary scoring",
    "Crossref / OpenAlex / NIH RePORTER tools in Agent runtime",
    "Conservative Researcher / Organization / Contact resolution",
    "Minimal evidence-backed official scoring draft",
    "Human-review email draft generation",
    "AI usage logging",
    "JSON / CSV export and Run Report",
]

NOT_IMPLEMENTED_CAPABILITIES = [
    "Real email sending",
    "Approval workflow for sending",
    "Database-backed production workspace",
    "ORCID identity resolution",
    "Automatic funding-to-PI merge by name",
    "Complete production scoring",
]

IMPLEMENTED_CAPABILITIES_ZH = [
    "PubMed ESearch / EFetch 检索",
    "原始数据保存",
    "论文解析和去重",
    "从 PubMed affiliation 文本中提取公开邮箱证据",
    "Lead 生成和去重",
    "基础机构和国家识别",
    "关键词匹配和 PubMed 临时评分",
    "Agent 可调用 Crossref / OpenAlex / NIH RePORTER 工具",
    "保守的研究者 / 机构 / 联系方式整理",
    "基于证据的官方评分草稿",
    "人工审核用邮件草稿生成",
    "AI 用量记录",
    "JSON / CSV 导出和运行报告",
]

NOT_IMPLEMENTED_CAPABILITIES_ZH = [
    "真实邮件发送",
    "邮件发送审批流程",
    "数据库版生产工作台",
    "ORCID 身份识别",
    "按姓名自动合并基金和 PI",
    "完整生产版评分",
]

LANGUAGE_OPTIONS = {"中文": "zh", "English": "en"}
DEFAULT_HELPER_LANGUAGE = "en"
DEFAULT_UI_LANGUAGE = "zh"

TRANSLATIONS = {
    "en": {
        "language_label": "Language / 语言",
        "app_caption": (
            "Evidence-backed literature lead discovery. No real email sending is "
            "available in this stage."
        ),
        "current_scope": "Current scope",
        "implemented": "Implemented",
        "not_implemented": "Not implemented",
        "agent_task": "Agent / natural language task",
        "agent_caption": (
            "Requires OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL for a real "
            "model run. Tool calls may access real public APIs. No email is sent."
        ),
        "task": "Task",
        "agent_max_turns": "Agent max_turns",
        "run_agent": "Run Agent",
        "running_agent": "Running Agent...",
        "agent_result": "Agent result",
        "tool_calls": "Tool calls",
        "data_sources": "Data sources",
        "turns": "Turns",
        "agent_messages": "Agent messages",
        "pubmed_search_task": "PubMed search task",
        "country_optional": "country optional",
        "service_type_optional": "service_type optional",
        "output_dirs": "Output directories",
        "run_pubmed_search": "Run PubMed search",
        "running_pubmed": "Running PubMed search. This calls the real PubMed API.",
        "pubmed_failed": "PubMed run failed",
        "empty_result_tip": "Run a PubMed task to view papers, leads, entities, scoring, and files.",
        "run_summary": "Run summary",
        "sources_tab": "Sources",
        "steps_tab": "Steps",
        "papers_tab": "Papers",
        "leads_tab": "Leads",
        "researchers_tab": "Researchers",
        "funding_tab": "Funding",
        "scoring_tab": "Scoring",
        "email_draft_tab": "Email Draft",
        "report_tab": "Report",
        "downloads_tab": "Downloads",
        "no_papers": "No papers parsed in this run.",
        "no_leads": "No leads generated in this run.",
        "country": "country",
        "priority": "priority",
        "email_status": "email_status",
        "no_researchers": "No leads available for researcher resolution.",
        "organizations": "Organizations",
        "no_funding": (
            "No funding records are attached to this view. Run Agent with "
            "search_funding or use NIH RePORTER tooling to collect explicit "
            "funding evidence."
        ),
        "no_scoring": "No leads available for scoring.",
        "scoring_caption": (
            "Official scoring draft uses explicit evidence only. Missing funding or "
            "outsourcing evidence keeps the official total score empty."
        ),
        "no_lead_selected": "No lead selected.",
        "select_lead": "Select Lead",
        "email_draft_title": "Human-review email draft",
        "email_draft_caption": "This creates an editable English draft only. It does not send email.",
        "service_context_optional": "service_context optional",
        "sender_name_optional": "sender_name optional",
        "sender_title_optional": "sender_title optional",
        "organization_name_optional": "organization_name optional",
        "generate_draft": "Generate draft",
        "calling_model": "Calling the configured model for a draft...",
        "draft_tip": "Generate a draft to edit and download it here.",
        "save_draft_edits": "Save draft edits",
        "draft_saved": "Draft saved in the current Streamlit session.",
        "download_draft_json": "Download draft JSON",
        "email_review_title": "Email review and permission",
        "email_review_decision": "Review decision",
        "reviewer_name": "reviewer name",
        "review_comments_optional": "review comments optional",
        "approve": "Approve",
        "reject": "Reject",
        "request_changes": "Request changes",
        "save_review_decision": "Save review decision",
        "review_saved": "Review decision saved. No email was sent.",
        "send_permission": "Send permission",
        "audit_record_path": "Audit record path",
        "download_papers_csv": "Download papers CSV",
        "download_papers_json": "Download papers JSON",
        "download_leads_csv": "Download leads CSV",
        "download_leads_json": "Download leads JSON",
        "download_run_report": "Download Run Report",
        "missing_file": "{label} file is missing: {path}",
        "ai_usage": "AI usage",
        "no_ai_usage": "No AI usage records yet.",
        "raw_files": "Raw files",
        "processed_files": "Processed files",
        "run_report_path": "Run report path",
        "all": "All",
    },
    "zh": {
        "language_label": "语言 / Language",
        "app_caption": "基于公开证据的科研客户线索发现。本阶段不会发送真实邮件。",
        "current_scope": "当前范围",
        "implemented": "已完成",
        "not_implemented": "未完成",
        "agent_task": "Agent / 自然语言任务",
        "agent_caption": (
            "真实模型运行需要配置 OPENAI_API_KEY、OPENAI_BASE_URL 和 OPENAI_MODEL。"
            "工具调用可能访问公开 API，但不会发送邮件。"
        ),
        "task": "任务",
        "agent_max_turns": "Agent 最大轮数",
        "run_agent": "运行 Agent",
        "running_agent": "Agent 运行中...",
        "agent_result": "Agent 结果",
        "tool_calls": "工具调用",
        "data_sources": "数据源",
        "turns": "轮数",
        "agent_messages": "Agent 消息",
        "pubmed_search_task": "PubMed 检索任务",
        "country_optional": "国家，可选",
        "service_type_optional": "服务类型，可选",
        "output_dirs": "输出目录",
        "run_pubmed_search": "运行 PubMed 检索",
        "running_pubmed": "正在运行 PubMed 检索，会访问真实 PubMed API。",
        "pubmed_failed": "PubMed 运行失败",
        "empty_result_tip": "运行一次 PubMed 任务后，可以查看论文、线索、实体、评分和文件。",
        "run_summary": "运行摘要",
        "sources_tab": "数据源",
        "steps_tab": "步骤",
        "papers_tab": "论文",
        "leads_tab": "线索",
        "researchers_tab": "研究者",
        "funding_tab": "基金",
        "scoring_tab": "评分",
        "email_draft_tab": "邮件草稿",
        "report_tab": "报告",
        "downloads_tab": "下载",
        "no_papers": "本次运行没有解析出论文。",
        "no_leads": "本次运行没有生成线索。",
        "country": "国家",
        "priority": "优先级",
        "email_status": "邮箱状态",
        "no_researchers": "当前没有可用于研究者整理的线索。",
        "organizations": "机构",
        "no_funding": "当前页面没有基金记录。可以通过 Agent 调用 search_funding 收集 NIH RePORTER 的明确基金证据。",
        "no_scoring": "当前没有可用于评分的线索。",
        "scoring_caption": "官方评分草稿只使用明确证据。基金或外包意向证据缺失时，官方总分会保持为空。",
        "no_lead_selected": "没有选择线索。",
        "select_lead": "选择线索",
        "email_draft_title": "人工审核邮件草稿",
        "email_draft_caption": "这里只生成可编辑英文草稿，不会发送邮件。",
        "service_context_optional": "服务说明，可选",
        "sender_name_optional": "发件人姓名，可选",
        "sender_title_optional": "发件人职位，可选",
        "organization_name_optional": "发件机构，可选",
        "generate_draft": "生成草稿",
        "calling_model": "正在调用已配置模型生成草稿...",
        "draft_tip": "生成草稿后可以在这里编辑并下载。",
        "save_draft_edits": "保存草稿修改",
        "draft_saved": "草稿已保存在当前 Streamlit 会话中。",
        "download_draft_json": "下载草稿 JSON",
        "email_review_title": "邮件审核与权限",
        "email_review_decision": "审核决定",
        "reviewer_name": "审核人姓名",
        "review_comments_optional": "审核意见，可选",
        "approve": "通过",
        "reject": "驳回",
        "request_changes": "需要修改",
        "save_review_decision": "保存审核决定",
        "review_saved": "审核决定已保存。本系统没有发送邮件。",
        "send_permission": "发送权限",
        "audit_record_path": "审计记录路径",
        "download_papers_csv": "下载论文 CSV",
        "download_papers_json": "下载论文 JSON",
        "download_leads_csv": "下载线索 CSV",
        "download_leads_json": "下载线索 JSON",
        "download_run_report": "下载运行报告",
        "missing_file": "{label} 文件不存在：{path}",
        "ai_usage": "AI 用量",
        "no_ai_usage": "还没有 AI 用量记录。",
        "raw_files": "原始文件",
        "processed_files": "处理后文件",
        "run_report_path": "运行报告路径",
        "all": "全部",
    },
}

TABLE_LABELS = {
    "Status": {"zh": "状态"},
    "PMIDs": {"zh": "PMID 数"},
    "Papers": {"zh": "论文数"},
    "Leads": {"zh": "线索数"},
    "Verified email leads": {"zh": "有验证邮箱的线索"},
    "Missing email": {"zh": "缺失邮箱"},
    "Started at": {"zh": "开始时间"},
    "Finished at": {"zh": "结束时间"},
    "Step": {"zh": "步骤"},
    "Evidence": {"zh": "证据"},
    "Source": {"zh": "数据源"},
    "Role": {"zh": "作用"},
    "Title": {"zh": "标题"},
    "Journal": {"zh": "期刊"},
    "Publication Year": {"zh": "发表年份"},
    "Authors": {"zh": "作者"},
    "Source URL": {"zh": "来源链接"},
    "Lead ID": {"zh": "线索 ID"},
    "PI / Candidate": {"zh": "PI / 候选人"},
    "Verified Email": {"zh": "验证邮箱"},
    "Email Status": {"zh": "邮箱状态"},
    "Institution": {"zh": "机构"},
    "Country": {"zh": "国家"},
    "Lead Score": {"zh": "线索分数"},
    "Priority": {"zh": "优先级"},
    "Data Quality": {"zh": "数据质量"},
    "Manual Review Required": {"zh": "需要人工审核"},
    "Researcher ID": {"zh": "研究者 ID"},
    "Name": {"zh": "姓名"},
    "Emails": {"zh": "邮箱"},
    "Organizations": {"zh": "机构"},
    "Merge Status": {"zh": "合并状态"},
    "Merge Reason": {"zh": "合并原因"},
    "Match Confidence": {"zh": "匹配置信度"},
    "Source Leads": {"zh": "来源线索"},
    "Organization ID": {"zh": "机构 ID"},
    "Aliases": {"zh": "别名"},
    "Source Records": {"zh": "来源记录"},
    "Official Total Score": {"zh": "官方总分"},
    "Scoring Status": {"zh": "评分状态"},
    "Missing Dimensions": {"zh": "缺失维度"},
    "Funding Score": {"zh": "基金分"},
    "Research Direction Score": {"zh": "方向匹配分"},
    "Publication Recency Score": {"zh": "发表时间分"},
    "Outsourcing Score": {"zh": "外包意向分"},
    "Grant ID": {"zh": "基金 ID"},
    "Agency": {"zh": "资助机构"},
    "Project Title": {"zh": "项目标题"},
    "PI Name": {"zh": "PI 姓名"},
    "Fiscal Year": {"zh": "财政年度"},
    "Amount": {"zh": "金额"},
    "Tool": {"zh": "工具"},
    "Called At": {"zh": "调用时间"},
    "Feature": {"zh": "功能"},
    "Model": {"zh": "模型"},
    "Input Tokens": {"zh": "输入 tokens"},
    "Output Tokens": {"zh": "输出 tokens"},
    "Total Tokens": {"zh": "总 tokens"},
    "Estimated Cost": {"zh": "预估费用"},
    "Currency": {"zh": "币种"},
    "Field": {"zh": "字段"},
    "Value": {"zh": "值"},
    "Confidence": {"zh": "置信度"},
    "Explanation": {"zh": "说明"},
    "Lead Detail": {"zh": "客户详情"},
    "Recent Paper": {"zh": "最近论文"},
    "Matched Keywords": {"zh": "命中关键词"},
    "Target Service": {"zh": "目标服务"},
    "Raw Affiliation": {"zh": "原始 affiliation"},
    "Data Source Links": {"zh": "数据源链接"},
    "Manual Review Reason": {"zh": "人工审核原因"},
    "Temporary Score": {"zh": "临时评分"},
    "Temporary Priority": {"zh": "临时优先级"},
    "Author Role": {"zh": "作者角色"},
    "Email Source": {"zh": "邮箱来源"},
    "Country Source": {"zh": "国家来源"},
}

VALUE_LABELS = {
    "used": {"zh": "已使用"},
    "available": {"zh": "可用"},
    "available via Agent": {"zh": "Agent 可用"},
    "Main paper and lead discovery path": {"zh": "主要论文和线索发现路径"},
    "DOI and publication metadata enrichment": {"zh": "DOI 和发表信息补充"},
    "Open literature graph enrichment": {"zh": "开放文献图谱补充"},
    "Explicit NIH funding evidence only": {"zh": "仅作为 NIH 明确基金证据"},
    "done": {"zh": "完成"},
    "UI/service validation": {"zh": "UI / service 验证"},
    "raw ESearch JSON": {"zh": "原始 ESearch JSON"},
    "raw EFetch XML": {"zh": "原始 EFetch XML"},
    "processed papers": {"zh": "处理后论文"},
    "processed leads": {"zh": "处理后线索"},
    "JSON / CSV / run report": {"zh": "JSON / CSV / 运行报告"},
    "Input validation": {"zh": "输入验证"},
    "Paper parsing": {"zh": "论文解析"},
    "Lead generation": {"zh": "线索生成"},
    "Export": {"zh": "导出"},
    "missing evidence": {"zh": "缺少证据"},
}


def normalize_language(language: str | None) -> str:
    """Normalize display language input into an internal language code."""

    if language in {"zh", "中文", "Chinese", "cn"}:
        return "zh"
    return "en"


def translate(key: str, language: str | None = None) -> str:
    """Translate a UI text key."""

    lang = normalize_language(language)
    return TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["en"].get(key, key)


def table_label(label: str, language: str | None = None) -> str:
    """Translate a table field label while keeping English as the default API."""

    lang = normalize_language(language)
    if lang == "en":
        return label
    return TABLE_LABELS.get(label, {}).get(lang, label)


def display_value(value: Any, language: str | None = None) -> Any:
    """Translate simple display values without changing underlying data objects."""

    if not isinstance(value, str):
        return value
    lang = normalize_language(language)
    if lang == "en":
        return value
    return VALUE_LABELS.get(value, {}).get(lang, value)


def build_summary_metrics(
    report: dict[str, Any],
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[tuple[str, Any]]:
    """Return ordered summary metrics for the Streamlit overview."""

    return [
        (table_label("Status", language), report.get("status", "unknown")),
        (table_label("PMIDs", language), report.get("pmid_count", 0)),
        (table_label("Papers", language), report.get("paper_count", 0)),
        (table_label("Leads", language), report.get("lead_count", 0)),
        (
            table_label("Verified email leads", language),
            report.get("leads_with_verified_email_count", 0),
        ),
        (table_label("Missing email", language), report.get("missing_email_count", 0)),
        (table_label("Started at", language), report.get("started_at") or ""),
        (table_label("Finished at", language), report.get("finished_at") or ""),
    ]


def build_workflow_step_rows(
    report: dict[str, Any],
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[dict[str, Any]]:
    """Build deterministic workflow rows for the run overview."""

    status = str(report.get("status") or "unknown")
    has_processed = bool(report.get("processed_files"))
    step_key = table_label("Step", language)
    status_key = table_label("Status", language)
    evidence_key = table_label("Evidence", language)
    return [
        {
            step_key: display_value("Input validation", language),
            status_key: display_value("done", language),
            evidence_key: display_value("UI/service validation", language),
        },
        {
            step_key: "PubMed ESearch",
            status_key: display_value(_step_status(status), language),
            evidence_key: display_value("raw ESearch JSON", language),
        },
        {
            step_key: "PubMed EFetch",
            status_key: display_value(_step_status(status), language),
            evidence_key: display_value("raw EFetch XML", language),
        },
        {
            step_key: display_value("Paper parsing", language),
            status_key: display_value("done" if has_processed else status, language),
            evidence_key: display_value("processed papers", language),
        },
        {
            step_key: display_value("Lead generation", language),
            status_key: display_value("done" if has_processed else status, language),
            evidence_key: display_value("processed leads", language),
        },
        {
            step_key: display_value("Export", language),
            status_key: display_value("done" if has_processed else status, language),
            evidence_key: display_value("JSON / CSV / run report", language),
        },
    ]


def build_data_source_rows(
    report: dict[str, Any],
    *,
    agent_messages: list[dict[str, Any]] | None = None,
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[dict[str, Any]]:
    """Return current data-source visibility rows."""

    used_sources = set(extract_tool_sources(agent_messages or []))
    queried_sources = report.get("queried_sources")
    if isinstance(queried_sources, list):
        used_sources.update(str(source) for source in queried_sources)
    used_sources.add("pubmed")

    return [
        {
            table_label("Source", language): "PubMed",
            table_label("Status", language): display_value(
                "used" if "pubmed" in used_sources else "available",
                language,
            ),
            table_label("Role", language): display_value(
                "Main paper and lead discovery path",
                language,
            ),
        },
        {
            table_label("Source", language): "Crossref",
            table_label("Status", language): display_value(
                "used" if "crossref" in used_sources else "available via Agent",
                language,
            ),
            table_label("Role", language): display_value(
                "DOI and publication metadata enrichment",
                language,
            ),
        },
        {
            table_label("Source", language): "OpenAlex",
            table_label("Status", language): display_value(
                "used" if "openalex" in used_sources else "available via Agent",
                language,
            ),
            table_label("Role", language): display_value(
                "Open literature graph enrichment",
                language,
            ),
        },
        {
            table_label("Source", language): "NIH RePORTER",
            table_label("Status", language): display_value(
                "used" if "nih_reporter" in used_sources else "available via Agent",
                language,
            ),
            table_label("Role", language): display_value(
                "Explicit NIH funding evidence only",
                language,
            ),
        },
    ]


def papers_to_table_rows(
    papers: list[PubMedPaper],
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[dict[str, Any]]:
    """Convert paper objects to rows suitable for UI display."""

    return [
        {
            table_label("PMID", language): paper.pmid,
            table_label("Title", language): paper.title,
            table_label("Journal", language): paper.journal,
            table_label("Publication Year", language): paper.publication_year or "",
            table_label("DOI", language): paper.doi or "",
            table_label("Authors", language): "; ".join(author.full_name for author in paper.authors),
            table_label("Source URL", language): paper.source_url,
        }
        for paper in papers
    ]


def leads_to_table_rows(
    leads: list[PubMedLead],
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[dict[str, Any]]:
    """Convert lead objects to rows suitable for UI display and filtering."""

    return [
        {
            table_label("Lead ID", language): lead.lead_id,
            table_label("PI / Candidate", language): lead.pi_full_name,
            table_label("Verified Email", language): lead.verified_email or "missing",
            table_label("Email Status", language): lead.email_status,
            table_label("Institution", language): lead.institution or "unknown",
            table_label("Country", language): lead.country,
            table_label("Lead Score", language): lead.lead_score,
            table_label("Priority", language): lead.priority,
            table_label("Data Quality", language): lead.data_quality,
            table_label("Manual Review Required", language): lead.manual_review_required,
        }
        for lead in leads
    ]


def researcher_rows_from_leads(
    leads: list[PubMedLead],
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[dict[str, Any]]:
    """Resolve leads into conservative researcher rows for display."""

    result = resolve_pubmed_leads_to_entities(leads)
    return [
        {
            table_label("Researcher ID", language): researcher.unified_id,
            table_label("Name", language): researcher.full_name,
            table_label("Emails", language): "; ".join(researcher.emails),
            table_label("Organizations", language): "; ".join(researcher.organizations),
            table_label("Country", language): researcher.country or "unknown",
            table_label("Merge Status", language): researcher.merge_status,
            table_label("Merge Reason", language): researcher.merge_reason or "",
            table_label("Match Confidence", language): researcher.match_confidence,
            table_label("Source Leads", language): "; ".join(researcher.source_lead_ids),
        }
        for researcher in result.researchers
    ]


def organization_rows_from_leads(
    leads: list[PubMedLead],
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[dict[str, Any]]:
    """Resolve leads into organization rows for display."""

    result = resolve_pubmed_leads_to_entities(leads)
    return [
        {
            table_label("Organization ID", language): organization.unified_id,
            table_label("Name", language): organization.name,
            table_label("Country", language): organization.country or "unknown",
            table_label("Aliases", language): "; ".join(organization.aliases),
            table_label("Merge Status", language): organization.merge_status,
            table_label("Merge Reason", language): organization.merge_reason or "",
            table_label("Source Records", language): "; ".join(organization.source_record_ids),
        }
        for organization in result.organizations
    ]


def official_score_rows_from_leads(
    leads: list[PubMedLead],
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[dict[str, Any]]:
    """Build official scoring draft rows for display."""

    rows: list[dict[str, Any]] = []
    for lead in leads:
        result = score_pubmed_lead_official_minimal(lead)
        rows.append(
            {
                table_label("Lead ID", language): lead.lead_id,
                table_label("PI / Candidate", language): lead.pi_full_name,
                table_label("Official Total Score", language): result.official_total_score
                if result.official_total_score is not None
                else display_value("missing evidence", language),
                table_label("Priority", language): result.priority,
                table_label("Scoring Status", language): result.scoring_status,
                table_label("Missing Dimensions", language): "; ".join(result.missing_dimensions),
                table_label("Funding Score", language): _dimension_score(
                    result,
                    "funding_activity",
                    language=language,
                ),
                table_label("Research Direction Score", language): _dimension_score(
                    result,
                    "research_direction_match",
                    language=language,
                ),
                table_label("Publication Recency Score", language): _dimension_score(
                    result,
                    "publication_recency",
                    language=language,
                ),
                table_label("Outsourcing Score", language): _dimension_score(
                    result,
                    "outsourcing_tendency",
                    language=language,
                ),
            }
        )
    return rows


def lead_manual_review_reason(lead: PubMedLead) -> str:
    """Return the first clear reason a lead still needs manual review."""

    if not lead.manual_review_required:
        return "not_required"
    if not lead.verified_email:
        return "missing_email_candidate"
    if lead.country == "unknown" or lead.country_confidence == "unknown":
        return "unknown_country"
    if lead.data_quality:
        return lead.data_quality
    return "needs_review"


def lead_detail_summary_rows(
    lead: PubMedLead,
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[dict[str, Any]]:
    """Build compact lead detail rows shared by UI and tests."""

    field_key = table_label("Field", language)
    value_key = table_label("Value", language)
    return [
        {field_key: table_label("PI / Candidate", language), value_key: lead.pi_full_name},
        {
            field_key: table_label("Verified Email", language),
            value_key: lead.verified_email or "missing",
        },
        {
            field_key: table_label("Institution", language),
            value_key: lead.institution or "unknown",
        },
        {field_key: table_label("Country", language), value_key: lead.country or "unknown"},
        {
            field_key: table_label("Recent Paper", language),
            value_key: lead.recent_publication_title or "unknown",
        },
        {
            field_key: table_label("Matched Keywords", language),
            value_key: _join_or_unknown(lead.matched_keywords),
        },
        {
            field_key: table_label("Target Service", language),
            value_key: lead.target_service_type or "unknown",
        },
        {field_key: table_label("PMID", language), value_key: lead.pmid or "unknown"},
        {field_key: table_label("DOI", language), value_key: lead.doi or "unknown"},
        {
            field_key: table_label("Manual Review Reason", language),
            value_key: lead_manual_review_reason(lead),
        },
    ]


def lead_detail_evidence_rows(
    lead: PubMedLead,
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[dict[str, Any]]:
    """Build field-level evidence rows without inventing missing facts."""

    field_key = table_label("Field", language)
    value_key = table_label("Value", language)
    source_key = table_label("Source", language)
    confidence_key = table_label("Confidence", language)
    evidence_key = table_label("Evidence", language)

    source_links = _join_or_unknown(lead.source_links)
    raw_affiliation = lead.raw_affiliation or "unknown"
    email_source = lead.email_source_type or "unknown"
    country_source = lead.country_source or "unknown"

    return [
        {
            field_key: table_label("PI / Candidate", language),
            value_key: lead.pi_full_name or "unknown",
            source_key: "PubMed author list",
            confidence_key: lead.author_role or "candidate",
            evidence_key: "Candidate lead only; corresponding-author status is not assumed.",
        },
        {
            field_key: table_label("Verified Email", language),
            value_key: lead.verified_email or "missing",
            source_key: email_source,
            confidence_key: lead.name_email_match_confidence or "unknown",
            evidence_key: lead.email_source_url or source_links,
        },
        {
            field_key: table_label("Institution", language),
            value_key: lead.institution or "unknown",
            source_key: table_label("Raw Affiliation", language),
            confidence_key: "affiliation_text" if lead.institution else "unknown",
            evidence_key: raw_affiliation,
        },
        {
            field_key: table_label("Country", language),
            value_key: lead.country or "unknown",
            source_key: country_source,
            confidence_key: lead.country_confidence or "unknown",
            evidence_key: raw_affiliation,
        },
        {
            field_key: table_label("Recent Paper", language),
            value_key: lead.recent_publication_title or "unknown",
            source_key: "PubMed",
            confidence_key: "source_record",
            evidence_key: f"PMID: {lead.pmid or 'unknown'}; URL: {source_links}",
        },
        {
            field_key: table_label("Matched Keywords", language),
            value_key: _join_or_unknown(lead.matched_keywords),
            source_key: "query matching rules",
            confidence_key: "rule_based",
            evidence_key: lead.target_service_type or "unknown",
        },
        {
            field_key: table_label("Temporary Score", language),
            value_key: lead.lead_score,
            source_key: "PubMed-only temporary scoring",
            confidence_key: "rule_based",
            evidence_key: lead.score_explanation or "unknown",
        },
        {
            field_key: table_label("Temporary Priority", language),
            value_key: lead.priority or "unscored",
            source_key: "PubMed-only temporary scoring",
            confidence_key: "rule_based",
            evidence_key: lead.score_explanation or "unknown",
        },
        {
            field_key: table_label("Manual Review Required", language),
            value_key: lead.manual_review_required,
            source_key: "data quality rules",
            confidence_key: lead.data_quality or "unknown",
            evidence_key: lead_manual_review_reason(lead),
        },
        {
            field_key: table_label("Data Source Links", language),
            value_key: source_links,
            source_key: "source_links",
            confidence_key: "source_record" if lead.source_links else "unknown",
            evidence_key: source_links,
        },
    ]


def _join_or_unknown(values: list[str] | tuple[str, ...] | None) -> str:
    """Join display values while making missing evidence explicit."""

    if not values:
        return "unknown"
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    if not cleaned:
        return "unknown"
    return "; ".join(cleaned)


def funding_rows_from_agent_messages(
    messages: list[dict[str, Any]] | None,
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[dict[str, Any]]:
    """Extract funding rows from Agent tool messages if search_funding ran."""

    rows: list[dict[str, Any]] = []
    for payload in _iter_tool_payloads(messages or []):
        data = payload.get("data")
        if not isinstance(data, dict) or data.get("source") != "nih_reporter":
            continue
        records = data.get("funding_records")
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            rows.append(
                {
                    table_label("Grant ID", language): record.get("grant_id", ""),
                    table_label("Agency", language): record.get("agency", ""),
                    table_label("Project Title", language): record.get("project_title", ""),
                    table_label("PI Name", language): record.get("pi_name", ""),
                    table_label("Institution", language): record.get("institution", ""),
                    table_label("Fiscal Year", language): record.get("fiscal_year", ""),
                    table_label("Amount", language): record.get("amount", ""),
                    table_label("Source URL", language): record.get("source_url", ""),
                }
            )
    return rows


def filter_lead_rows(
    rows: list[dict[str, Any]],
    *,
    country: str | None = None,
    priority: str | None = None,
    email_status: str | None = None,
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[dict[str, Any]]:
    """Filter lead rows by optional UI filter values."""

    return [
        row
        for row in rows
        if _matches_optional_filter(row.get(table_label("Country", language)), country)
        and _matches_optional_filter(row.get(table_label("Priority", language)), priority)
        and _matches_optional_filter(row.get(table_label("Email Status", language)), email_status)
    ]


def get_filter_options(
    rows: list[dict[str, Any]],
    field_name: str,
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> list[str]:
    """Build stable selectbox options from row values."""

    values = {
        str(row.get(field_name, "")).strip()
        for row in rows
        if str(row.get(field_name, "")).strip()
    }
    return [translate("all", language), *sorted(values)]


def path_to_text(path: Path | str | None) -> str:
    """Return a readable path string for UI output."""

    if path is None:
        return ""
    return str(path)


def main() -> None:
    """Run the Streamlit application."""

    import streamlit as st

    st.set_page_config(
        page_title="ScholarLead Agent",
        layout="wide",
    )
    _render_app(st)


def _render_app(st: Any) -> None:
    selected_language = st.sidebar.radio(
        translate("language_label", DEFAULT_UI_LANGUAGE),
        list(LANGUAGE_OPTIONS),
        index=0,
        horizontal=True,
    )
    language = normalize_language(LANGUAGE_OPTIONS[selected_language])

    st.title("ScholarLead Agent")
    st.caption(translate("app_caption", language))

    _render_capability_overview(st, language)
    _render_agent_task_area(st, language)
    _render_search_form(st, language)

    result = st.session_state.get("pubmed_run_result")
    if result is None:
        st.info(translate("empty_result_tip", language))
        _render_ai_usage_area(st, language)
        return

    _render_result(st, result, language)
    _render_ai_usage_area(st, language)


def _render_capability_overview(st: Any, language: str) -> None:
    with st.expander(translate("current_scope", language), expanded=True):
        left, right = st.columns(2)
        implemented = (
            IMPLEMENTED_CAPABILITIES_ZH
            if normalize_language(language) == "zh"
            else IMPLEMENTED_CAPABILITIES
        )
        not_implemented = (
            NOT_IMPLEMENTED_CAPABILITIES_ZH
            if normalize_language(language) == "zh"
            else NOT_IMPLEMENTED_CAPABILITIES
        )
        left.subheader(translate("implemented", language))
        left.write("\n".join(f"- {item}" for item in implemented))
        right.subheader(translate("not_implemented", language))
        right.write("\n".join(f"- {item}" for item in not_implemented))


def _render_agent_task_area(st: Any, language: str) -> None:
    with st.expander(translate("agent_task", language), expanded=False):
        st.caption(translate("agent_caption", language))
        task = st.text_area(
            translate("task", language),
            value=(
                "Find 5 PubMed papers since 2025 about single-cell cancer, "
                "then supplement metadata and NIH funding evidence when useful."
            ),
            height=100,
        )
        max_turns = st.number_input(
            translate("agent_max_turns", language),
            min_value=1,
            max_value=10,
            value=6,
            step=1,
        )
        submitted = st.button(translate("run_agent", language))

        if not submitted:
            _render_last_agent_result(st, language)
            return
        with st.spinner(translate("running_agent", language)):
            try:
                conversation_id, result, task_context = run_agent_conversation(
                    task,
                    conversation_id=st.session_state.get("agent_conversation_id"),
                    max_turns=int(max_turns),
                )
            except (AgentRunError, LLMAdapterError, ValueError) as error:
                st.error(str(error))
                return

        st.session_state["agent_conversation_id"] = conversation_id
        st.session_state["agent_run_result"] = result
        st.session_state["agent_task_context"] = task_context
        _render_last_agent_result(st, language)


def _render_last_agent_result(st: Any, language: str) -> None:
    result = st.session_state.get("agent_run_result")
    if result is None:
        return

    st.subheader(translate("agent_result", language))
    st.write(result.final_answer)
    tool_names = extract_tool_names(result.messages)
    tool_sources = extract_tool_sources(result.messages)
    run_reports = extract_run_report_paths(result.messages)
    cols = st.columns(3)
    cols[0].metric(translate("tool_calls", language), len(tool_names))
    cols[1].metric(translate("data_sources", language), len(tool_sources))
    cols[2].metric(translate("turns", language), result.turns)
    st.dataframe(
        [
            {
                table_label("Tool", language): tool,
                table_label("Source", language): source
                if index < len(tool_sources)
                else "",
            }
            for index, tool in enumerate(tool_names)
            for source in [tool_sources[index] if index < len(tool_sources) else ""]
        ],
        use_container_width=True,
        hide_index=True,
    )
    if run_reports:
        st.write({translate("run_report_path", language): run_reports})
    with st.expander(translate("agent_messages", language)):
        st.json(result.messages)


def _render_search_form(st: Any, language: str) -> None:
    with st.form("pubmed_search_form"):
        st.subheader(translate("pubmed_search_task", language))
        query = st.text_input("query", value="single-cell RNA sequencing cancer")
        col_a, col_b, col_c = st.columns(3)
        from_date = col_a.date_input("from_date", value=date(2024, 1, 1))
        to_date = col_b.date_input("to_date", value=date(2024, 12, 31))
        max_results = col_c.number_input(
            "max_results",
            min_value=1,
            max_value=PUBMED_MAX_RESULTS_LIMIT,
            value=min(5, PUBMED_MAX_RESULTS_LIMIT),
            step=1,
        )
        country = st.text_input(translate("country_optional", language), value="")
        service_type = st.text_input(translate("service_type_optional", language), value="")

        with st.expander(translate("output_dirs", language)):
            raw_dir = st.text_input("raw_dir", value="data/raw/pubmed")
            processed_dir = st.text_input(
                "processed_dir",
                value="data/processed/pubmed",
            )

        submitted = st.form_submit_button(translate("run_pubmed_search", language))

    if not submitted:
        return

    try:
        params = validate_pubmed_search_inputs(
            query=query,
            from_date=from_date.isoformat(),
            to_date=to_date.isoformat(),
            max_results=int(max_results),
            country=country,
            service_type=service_type,
            raw_dir=Path(raw_dir),
            processed_dir=Path(processed_dir),
        )
    except ValueError as error:
        st.error(str(error))
        return

    with st.spinner(translate("running_pubmed", language)):
        try:
            st.session_state["pubmed_run_result"] = run_pubmed_search(params)
        except Exception as error:
            st.error(f"{translate('pubmed_failed', language)}: {error}")


def _render_result(st: Any, result: PubMedRunResult, language: str) -> None:
    st.subheader(translate("run_summary", language))
    metrics = build_summary_metrics(result.run_report, language=language)
    columns = st.columns(4)
    for index, (label, value) in enumerate(metrics):
        columns[index % 4].metric(label, value)

    tabs = st.tabs(
        [
            translate("sources_tab", language),
            translate("steps_tab", language),
            translate("papers_tab", language),
            translate("leads_tab", language),
            translate("researchers_tab", language),
            translate("funding_tab", language),
            translate("scoring_tab", language),
            translate("email_draft_tab", language),
            translate("report_tab", language),
            translate("downloads_tab", language),
        ]
    )

    with tabs[0]:
        agent_result = st.session_state.get("agent_run_result")
        messages = agent_result.messages if agent_result is not None else None
        st.dataframe(
            build_data_source_rows(
                result.run_report,
                agent_messages=messages,
                language=language,
            ),
            use_container_width=True,
            hide_index=True,
        )

    with tabs[1]:
        st.dataframe(
            build_workflow_step_rows(result.run_report, language=language),
            use_container_width=True,
            hide_index=True,
        )

    with tabs[2]:
        _render_papers(st, result.papers, language)

    with tabs[3]:
        _render_leads(st, result.leads, language)

    with tabs[4]:
        _render_researchers(st, result.leads, language)

    with tabs[5]:
        _render_funding(st, language)

    with tabs[6]:
        _render_scoring(st, result.leads, language)

    with tabs[7]:
        _render_lead_detail(st, result.leads, language)

    with tabs[8]:
        _render_report(st, result, language)

    with tabs[9]:
        _render_downloads(st, result, language)


def _render_papers(st: Any, papers: list[PubMedPaper], language: str) -> None:
    rows = papers_to_table_rows(papers, language=language)
    if not rows:
        st.info(translate("no_papers", language))
        return
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_leads(st: Any, leads: list[PubMedLead], language: str) -> None:
    rows = leads_to_table_rows(leads, language=language)
    if not rows:
        st.info(translate("no_leads", language))
        return

    country_col, priority_col, email_col = st.columns(3)
    country_field = table_label("Country", language)
    priority_field = table_label("Priority", language)
    email_status_field = table_label("Email Status", language)
    selected_country = country_col.selectbox(
        translate("country", language),
        get_filter_options(rows, country_field, language=language),
    )
    selected_priority = priority_col.selectbox(
        translate("priority", language),
        get_filter_options(rows, priority_field, language=language),
    )
    selected_email_status = email_col.selectbox(
        translate("email_status", language),
        get_filter_options(rows, email_status_field, language=language),
    )
    filtered_rows = filter_lead_rows(
        rows,
        country=selected_country,
        priority=selected_priority,
        email_status=selected_email_status,
        language=language,
    )
    st.dataframe(filtered_rows, use_container_width=True, hide_index=True)


def _render_researchers(st: Any, leads: list[PubMedLead], language: str) -> None:
    if not leads:
        st.info(translate("no_researchers", language))
        return
    st.dataframe(
        researcher_rows_from_leads(leads, language=language),
        use_container_width=True,
        hide_index=True,
    )
    with st.expander(translate("organizations", language)):
        st.dataframe(
            organization_rows_from_leads(leads, language=language),
            use_container_width=True,
            hide_index=True,
        )


def _render_funding(st: Any, language: str) -> None:
    agent_result = st.session_state.get("agent_run_result")
    messages = agent_result.messages if agent_result is not None else None
    rows = funding_rows_from_agent_messages(messages, language=language)
    if not rows:
        st.info(translate("no_funding", language))
        return
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_scoring(st: Any, leads: list[PubMedLead], language: str) -> None:
    if not leads:
        st.info(translate("no_scoring", language))
        return
    st.caption(translate("scoring_caption", language))
    st.dataframe(
        official_score_rows_from_leads(leads, language=language),
        use_container_width=True,
        hide_index=True,
    )


def _render_lead_detail(st: Any, leads: list[PubMedLead], language: str) -> None:
    if not leads:
        st.info(translate("no_lead_selected", language))
        return

    lead_by_label = {
        f"{lead.pi_full_name} | {lead.pmid} | {lead.verified_email or 'missing'}": lead
        for lead in leads
    }
    selected_label = st.selectbox(translate("select_lead", language), list(lead_by_label))
    lead = lead_by_label[selected_label]

    st.subheader(table_label("Lead Detail", language))
    st.dataframe(
        lead_detail_summary_rows(lead, language=language),
        use_container_width=True,
        hide_index=True,
    )
    st.subheader(table_label("Evidence", language))
    st.dataframe(
        lead_detail_evidence_rows(lead, language=language),
        use_container_width=True,
        hide_index=True,
    )
    st.text_area(table_label("Raw Affiliation", language), value=lead.raw_affiliation or "", height=100)
    _render_email_draft_panel(st, lead, language)


def _render_email_draft_panel(st: Any, lead: PubMedLead, language: str) -> None:
    with st.expander(translate("email_draft_title", language), expanded=False):
        st.caption(translate("email_draft_caption", language))

        if st.button(translate("generate_draft", language), key=f"generate_email_draft_{lead.lead_id}"):
            try:
                evidence = build_auto_email_draft_input_from_lead(lead)
            except ValueError as error:
                st.error(str(error))
                return
            except EmailDraftGenerationError as error:
                st.warning(str(error))
                return

            with st.spinner(translate("calling_model", language)):
                try:
                    draft = EmailDraftService().generate(evidence)
                except EmailDraftGenerationError as error:
                    st.error(str(error))
                    return

            drafts_by_lead = st.session_state.setdefault("email_drafts_by_lead_id", {})
            drafts_by_lead[lead.lead_id] = email_draft_to_dict(draft)

        draft_data = st.session_state.get("email_drafts_by_lead_id", {}).get(
            lead.lead_id
        )
        if not draft_data:
            st.info(translate("draft_tip", language))
            return

        st.write(
            {
                "draft_status": draft_data.get("draft_status"),
                "model_name": draft_data.get("model_name"),
                "generated_at": draft_data.get("generated_at"),
                "can_send": draft_data.get("can_send"),
                "warnings": draft_data.get("warnings", []),
            }
        )
        evidence_data = draft_data.get("evidence") or {}
        match_data = evidence_data.get("matched_service") or {}
        sender_data = evidence_data.get("sender_profile") or {}
        st.subheader("Service match / 业务匹配")
        st.write(
            {
                "service_name": match_data.get("service_name"),
                "match_score": match_data.get("match_score"),
                "status": match_data.get("status"),
                "match_reason": match_data.get("match_reason"),
                "matched_terms": match_data.get("matched_terms"),
                "catalog_version": match_data.get("catalog_version"),
                "matcher_version": match_data.get("matcher_version"),
            }
        )
        st.subheader("Sender profile / 固定发件人")
        st.write(
            {
                "sender_name": evidence_data.get("sender_name"),
                "sender_title": evidence_data.get("sender_title"),
                "organization_name": evidence_data.get("organization_name"),
                "profile_version": sender_data.get("profile_version"),
            }
        )
        edited_subject = st.text_input(
            "subject",
            value=str(draft_data.get("subject", "")),
            key=f"draft_subject_{lead.lead_id}",
        )
        edited_body = st.text_area(
            "body",
            value=str(draft_data.get("body", "")),
            height=260,
            key=f"draft_body_{lead.lead_id}",
        )
        if st.button(translate("save_draft_edits", language), key=f"save_email_draft_{lead.lead_id}"):
            updated = dict(draft_data)
            updated["subject"] = edited_subject
            updated["body"] = edited_body
            updated["draft_status"] = "edited"
            st.session_state["email_drafts_by_lead_id"][lead.lead_id] = updated
            draft_data = updated
            st.success(translate("draft_saved", language))

        draft_data = _render_email_review_panel(st, lead, draft_data, language)
        _render_email_test_send_panel(st, lead, draft_data, language)

        st.download_button(
            label=translate("download_draft_json", language),
            data=json.dumps(draft_data, ensure_ascii=False, indent=2),
            file_name=f"{lead.lead_id}_email_draft.json",
            mime="application/json",
            key=f"download_email_draft_{lead.lead_id}",
        )


def _render_email_review_panel(
    st: Any,
    lead: PubMedLead,
    draft_data: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    st.subheader(translate("email_review_title", language))
    decision_options = ["approve", "reject", "request_changes"]
    decision_labels = {
        "approve": translate("approve", language),
        "reject": translate("reject", language),
        "request_changes": translate("request_changes", language),
    }
    decision = st.selectbox(
        translate("email_review_decision", language),
        decision_options,
        format_func=lambda value: decision_labels[value],
        key=f"review_decision_{lead.lead_id}",
    )
    reviewer = st.text_input(
        translate("reviewer_name", language),
        value=str(draft_data.get("human_reviewer") or ""),
        key=f"reviewer_name_{lead.lead_id}",
    )
    comments = st.text_area(
        translate("review_comments_optional", language),
        value=str(draft_data.get("review_comments") or ""),
        height=80,
        key=f"review_comments_{lead.lead_id}",
    )

    current_permission = evaluate_send_permission(draft_data)
    st.write(
        {
            translate("send_permission", language): current_permission.status,
            "can_send": current_permission.allowed,
            "blockers": current_permission.blockers,
            "warnings": current_permission.warnings,
        }
    )

    if not st.button(
        translate("save_review_decision", language),
        key=f"save_review_decision_{lead.lead_id}",
    ):
        return draft_data

    status_before = str(draft_data.get("draft_status") or "")
    try:
        updated = apply_email_review_decision(
            draft_data,
            EmailReviewDecision(
                reviewer=reviewer,
                decision=decision,
                comments=comments,
                edited_subject=str(draft_data.get("subject") or ""),
                edited_body=str(draft_data.get("body") or ""),
            ),
        )
    except ValueError as error:
        st.error(str(error))
        return draft_data

    permission = evaluate_send_permission(updated)
    audit_record = build_email_audit_record(
        event_type="email_review_decision",
        lead_id=lead.lead_id,
        actor=reviewer,
        status_before=status_before,
        status_after=str(updated.get("draft_status") or ""),
        permission=permission,
        note=comments,
        metadata={"ui": "streamlit", "pmid": lead.pmid},
    )
    audit_path = load_config().email_audit_dir / "email_audit.jsonl"
    append_email_audit_record(audit_record, audit_path)

    st.session_state["email_drafts_by_lead_id"][lead.lead_id] = updated
    audit_records = st.session_state.setdefault("email_audit_records", [])
    audit_records.append(email_audit_record_to_dict(audit_record))
    st.success(translate("review_saved", language))
    st.write({translate("audit_record_path", language): str(audit_path)})
    return updated


def _render_email_test_send_panel(
    st: Any,
    lead: PubMedLead,
    draft_data: dict[str, Any],
    language: str,
) -> None:
    st.subheader("测试邮件发送 / Test email sending")
    st.caption(
        "第一版真实发送只发到 .env 中的 EMAIL_TEST_RECIPIENT，"
        "不会默认发给检索到的 PI 邮箱。"
    )
    config = load_config()
    preview = build_test_send_preview(draft_data, config)
    st.write(
        {
            "mode": preview["mode"],
            "provider": preview["provider"],
            "send_enabled": preview["send_enabled"],
            "original_pi_email": preview["original_recipient"],
            "actual_test_recipient": preview["actual_recipient"],
            "sender": preview["sender"],
            "daily_limit": preview["daily_limit"],
            "allowed": preview["allowed"],
            "blockers": preview["blockers"],
        }
    )

    confirm = st.checkbox(
        "我确认这是测试发送，并且实际收件人是 EMAIL_TEST_RECIPIENT。",
        key=f"confirm_test_send_{lead.lead_id}",
    )
    if not st.button(
        "发送测试邮件 / Send test email",
        key=f"send_test_email_{lead.lead_id}",
        disabled=not confirm,
    ):
        return

    actor = str(draft_data.get("human_reviewer") or "streamlit_user")
    audit_path = config.email_audit_dir / "email_audit.jsonl"
    sent_today = _count_email_sends_today(config.database_path)
    result = send_reviewed_test_email(
        draft_data,
        actor=actor,
        config=config,
        draft_id=str(draft_data.get("draft_id") or lead.lead_id),
        audit_path=audit_path,
        sent_today=sent_today,
    )
    result_data = email_send_result_to_dict(result)
    _persist_email_send_result(
        database_path=config.database_path,
        lead=lead,
        draft_data=draft_data,
        draft_id=str(draft_data.get("draft_id") or lead.lead_id),
        result_data=result_data,
    )

    send_results = st.session_state.setdefault("email_send_results", [])
    send_results.append(result_data)
    st.write(result_data)
    if result.status == "sent":
        st.success("测试邮件已发送。")
    elif result.status == "blocked":
        st.warning("测试邮件被权限规则拦截，未发送。")
    else:
        st.error("测试邮件发送失败，已记录 failed。")


def _persist_email_send_result(
    *,
    database_path: Path,
    lead: PubMedLead,
    draft_data: dict[str, Any],
    draft_id: str,
    result_data: dict[str, Any],
) -> None:
    with initialize_database(database_path) as connection:
        insert_pubmed_lead(connection, lead)
        insert_email_draft(connection, draft_data, draft_id=draft_id)
        insert_email_send_log(connection, result_data)


def _count_email_sends_today(database_path: Path) -> int:
    today = date.today().isoformat()
    with initialize_database(database_path) as connection:
        row = fetch_one(
            connection,
            """
            SELECT COUNT(*) AS count
            FROM email_send_logs
            WHERE status = 'sent' AND attempted_at LIKE ?
            """,
            (f"{today}%",),
        )
    if row is None:
        return 0
    return int(row.get("count") or 0)


def _render_report(st: Any, result: PubMedRunResult, language: str) -> None:
    st.write(
        {
            translate("raw_files", language): result.run_report.get("raw_files", {}),
            translate("processed_files", language): result.run_report.get("processed_files", {}),
            translate("run_report_path", language): path_to_text(result.run_report_path),
        }
    )
    st.json(result.run_report)


def _render_downloads(st: Any, result: PubMedRunResult, language: str) -> None:
    if st.button("Generate Result Package v1 / 生成结果包 v1"):
        package = build_result_package_from_pubmed_result(result)
        st.success(f"Result Package created: {package.paths.package_dir}")
        st.write(
            {
                "workbook": str(package.paths.workbook_xlsx),
                "customers_csv": str(package.paths.customers_csv),
                "papers_csv": str(package.paths.papers_csv),
                "funding_csv": str(package.paths.funding_csv),
                "evidence_csv": str(package.paths.evidence_csv),
                "service_matches_csv": str(package.paths.service_matches_csv),
                "email_drafts_csv": str(package.paths.email_drafts_csv),
                "task_summary_json": str(package.paths.task_summary_json),
            }
        )

    _download_button_for_file(
        st,
        translate("download_papers_csv", language),
        result.processed_paths.papers_csv,
        "text/csv",
        language,
    )
    _download_button_for_file(
        st,
        translate("download_papers_json", language),
        result.processed_paths.papers_json,
        "application/json",
        language,
    )
    _download_button_for_file(
        st,
        translate("download_leads_csv", language),
        result.processed_paths.leads_csv,
        "text/csv",
        language,
    )
    _download_button_for_file(
        st,
        translate("download_leads_json", language),
        result.processed_paths.leads_json,
        "application/json",
        language,
    )
    _download_button_for_file(
        st,
        translate("download_run_report", language),
        result.run_report_path,
        "application/json",
        language,
    )


def _render_ai_usage_area(st: Any, language: str) -> None:
    with st.expander(translate("ai_usage", language), expanded=False):
        config = load_config()
        records = load_ai_usage_records(config.ai_usage_dir, limit=20)
        summary = summarize_ai_usage(records)
        st.write(
            {
                "usage_dir": str(config.ai_usage_dir),
                "threshold_notification": "pending final admin module",
                **summary,
            }
        )
        if not records:
            st.info(translate("no_ai_usage", language))
            return
        rows = [
            {
                table_label("Called At", language): record.get("called_at"),
                table_label("Feature", language): record.get("feature_module"),
                table_label("Model", language): record.get("model_name"),
                table_label("Input Tokens", language): record.get("input_tokens"),
                table_label("Output Tokens", language): record.get("output_tokens"),
                table_label("Total Tokens", language): record.get("total_tokens"),
                table_label("Estimated Cost", language): record.get("estimated_cost"),
                table_label("Currency", language): record.get("currency"),
                table_label("Status", language): record.get("status"),
            }
            for record in records
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _download_button_for_file(
    st: Any,
    label: str,
    path: Path,
    mime: str,
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> None:
    if not path.exists():
        st.warning(translate("missing_file", language).format(label=label, path=path))
        return

    st.download_button(
        label=label,
        data=path.read_bytes(),
        file_name=path.name,
        mime=mime,
    )


def _dimension_score(
    result: Any,
    name: str,
    language: str | None = DEFAULT_HELPER_LANGUAGE,
) -> Any:
    dimension = result.dimensions[name]
    return (
        dimension.score
        if dimension.score is not None
        else display_value("missing evidence", language)
    )


def _iter_tool_payloads(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") != "tool":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _matches_optional_filter(value: Any, selected: str | None) -> bool:
    if selected is None or selected == "" or selected in {"All", "全部"}:
        return True
    return str(value) == selected


def _step_status(run_status: str) -> str:
    if run_status == "success":
        return "done"
    return run_status


if __name__ == "__main__":
    main()
