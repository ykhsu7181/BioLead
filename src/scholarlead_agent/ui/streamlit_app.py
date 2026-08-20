"""Streamlit UI for the PubMed first-round workflow.

The UI is intentionally thin: it validates user input, calls the shared
PubMed service, displays returned objects, and downloads files already written
by the storage layer.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from scholarlead_agent.pubmed_models import (
    PUBMED_MAX_RESULTS_LIMIT,
    PubMedLead,
    PubMedPaper,
    validate_pubmed_search_inputs,
)
from scholarlead_agent.services.pubmed_service import PubMedRunResult, run_pubmed_search


IMPLEMENTED_CAPABILITIES = [
    "PubMed ESearch / EFetch",
    "raw 保存",
    "Paper 解析",
    "邮箱证据",
    "Lead 生成",
    "Lead 去重",
    "国家 / 机构识别",
    "关键词匹配",
    "PubMed 单源临时评分",
    "JSON / CSV 导出",
    "Run Report",
]

NOT_IMPLEMENTED_CAPABILITIES = [
    "Crossref",
    "基金源",
    "正式四维评分",
    "LLM / Agent",
    "个性化邮件",
    "真实邮件发送",
    "完整后台管理",
]


def build_summary_metrics(report: dict[str, Any]) -> list[tuple[str, Any]]:
    """Return ordered summary metrics for the Streamlit overview."""

    return [
        ("Status", report.get("status", "unknown")),
        ("PMIDs", report.get("pmid_count", 0)),
        ("Papers", report.get("paper_count", 0)),
        ("Leads", report.get("lead_count", 0)),
        ("Verified email leads", report.get("leads_with_verified_email_count", 0)),
        ("Missing email", report.get("missing_email_count", 0)),
        ("Started at", report.get("started_at") or ""),
        ("Finished at", report.get("finished_at") or ""),
    ]


def papers_to_table_rows(papers: list[PubMedPaper]) -> list[dict[str, Any]]:
    """Convert paper objects to rows suitable for UI display."""

    return [
        {
            "PMID": paper.pmid,
            "Title": paper.title,
            "Journal": paper.journal,
            "Publication Year": paper.publication_year or "",
            "DOI": paper.doi or "",
            "Authors": "; ".join(author.full_name for author in paper.authors),
            "Source URL": paper.source_url,
        }
        for paper in papers
    ]


def leads_to_table_rows(leads: list[PubMedLead]) -> list[dict[str, Any]]:
    """Convert lead objects to rows suitable for UI display and filtering."""

    return [
        {
            "Lead ID": lead.lead_id,
            "PI / Candidate": lead.pi_full_name,
            "Verified Email": lead.verified_email or "missing",
            "Email Status": lead.email_status,
            "Institution": lead.institution or "unknown",
            "Country": lead.country,
            "Lead Score": lead.lead_score,
            "Priority": lead.priority,
            "Data Quality": lead.data_quality,
            "Manual Review Required": lead.manual_review_required,
        }
        for lead in leads
    ]


def filter_lead_rows(
    rows: list[dict[str, Any]],
    *,
    country: str | None = None,
    priority: str | None = None,
    email_status: str | None = None,
) -> list[dict[str, Any]]:
    """Filter lead rows by optional UI filter values."""

    return [
        row
        for row in rows
        if _matches_optional_filter(row.get("Country"), country)
        and _matches_optional_filter(row.get("Priority"), priority)
        and _matches_optional_filter(row.get("Email Status"), email_status)
    ]


def get_filter_options(rows: list[dict[str, Any]], field_name: str) -> list[str]:
    """Build stable selectbox options from row values."""

    values = {
        str(row.get(field_name, "")).strip()
        for row in rows
        if str(row.get(field_name, "")).strip()
    }
    return ["All", *sorted(values)]


def path_to_text(path: Path | str | None) -> str:
    """Return a readable path string for UI output."""

    if path is None:
        return ""
    return str(path)


def main() -> None:
    """Run the Streamlit application."""

    import streamlit as st

    st.set_page_config(
        page_title="ScholarLead Agent PubMed",
        layout="wide",
    )
    _render_app(st)


def _render_app(st: Any) -> None:
    st.title("ScholarLead Agent - PubMed first round")
    st.caption(
        "轻量演示界面：复用现有 PubMed 主链路，不调用 LLM，不发送真实邮件。"
    )

    _render_capability_overview(st)
    _render_search_form(st)

    result = st.session_state.get("pubmed_run_result")
    if result is None:
        st.info("填写参数并点击运行后，这里会展示 Papers、Leads 和 Run Report。")
        return

    _render_result(st, result)


def _render_capability_overview(st: Any) -> None:
    with st.expander("当前阶段能力边界", expanded=True):
        implemented_col, not_implemented_col = st.columns(2)
        implemented_col.subheader("已具备")
        implemented_col.write("\n".join(f"- {item}" for item in IMPLEMENTED_CAPABILITIES))
        not_implemented_col.subheader("未实现")
        not_implemented_col.write(
            "\n".join(f"- {item}" for item in NOT_IMPLEMENTED_CAPABILITIES)
        )


def _render_search_form(st: Any) -> None:
    with st.form("pubmed_search_form"):
        st.subheader("PubMed 检索任务")
        query = st.text_input("query", value="single-cell RNA sequencing cancer")
        from_date = st.date_input("from_date", value=date(2024, 1, 1))
        to_date = st.date_input("to_date", value=date(2024, 12, 31))
        max_results = st.number_input(
            "max_results",
            min_value=1,
            max_value=PUBMED_MAX_RESULTS_LIMIT,
            value=min(5, PUBMED_MAX_RESULTS_LIMIT),
            step=1,
        )
        country = st.text_input("country（可选）", value="")
        service_type = st.text_input("service_type（可选）", value="")

        with st.expander("输出目录"):
            raw_dir = st.text_input("raw_dir", value="data/raw/pubmed")
            processed_dir = st.text_input(
                "processed_dir",
                value="data/processed/pubmed",
            )

        submitted = st.form_submit_button("运行 PubMed 检索")

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

    with st.spinner("正在执行 PubMed 检索，会访问真实 PubMed API..."):
        try:
            st.session_state["pubmed_run_result"] = run_pubmed_search(params)
        except Exception as error:
            st.error(f"PubMed run failed: {error}")


def _render_result(st: Any, result: PubMedRunResult) -> None:
    st.subheader("任务执行摘要")
    metrics = build_summary_metrics(result.run_report)
    columns = st.columns(4)
    for index, (label, value) in enumerate(metrics):
        columns[index % 4].metric(label, value)

    papers_tab, leads_tab, detail_tab, report_tab, download_tab = st.tabs(
        ["Papers", "Leads", "Lead 详情", "Run Report", "下载"]
    )

    with papers_tab:
        _render_papers(st, result.papers)

    with leads_tab:
        _render_leads(st, result.leads)

    with detail_tab:
        _render_lead_detail(st, result.leads)

    with report_tab:
        _render_report(st, result)

    with download_tab:
        _render_downloads(st, result)


def _render_papers(st: Any, papers: list[PubMedPaper]) -> None:
    rows = papers_to_table_rows(papers)
    if not rows:
        st.info("本次没有解析到 Papers。")
        return
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_leads(st: Any, leads: list[PubMedLead]) -> None:
    rows = leads_to_table_rows(leads)
    if not rows:
        st.info("本次没有生成 Leads。")
        return

    country, priority, email_status = st.columns(3)
    selected_country = country.selectbox(
        "country",
        get_filter_options(rows, "Country"),
    )
    selected_priority = priority.selectbox(
        "priority",
        get_filter_options(rows, "Priority"),
    )
    selected_email_status = email_status.selectbox(
        "email_status",
        get_filter_options(rows, "Email Status"),
    )
    filtered_rows = filter_lead_rows(
        rows,
        country=selected_country,
        priority=selected_priority,
        email_status=selected_email_status,
    )
    st.dataframe(filtered_rows, use_container_width=True, hide_index=True)


def _render_lead_detail(st: Any, leads: list[PubMedLead]) -> None:
    if not leads:
        st.info("本次没有 Lead 详情。")
        return

    lead_by_label = {
        f"{lead.pi_full_name} | {lead.pmid} | {lead.verified_email or 'missing'}": lead
        for lead in leads
    }
    selected_label = st.selectbox("选择 Lead", list(lead_by_label))
    lead = lead_by_label[selected_label]

    left, right = st.columns(2)
    left.write(
        {
            "姓名": lead.pi_full_name,
            "作者角色": lead.author_role,
            "机构": lead.institution or "unknown",
            "国家": lead.country,
            "国家置信度": lead.country_confidence,
            "国家来源": lead.country_source,
            "邮箱": lead.verified_email or "missing",
            "邮箱状态": lead.email_status,
            "邮箱来源": lead.email_source_type,
            "邮箱来源链接": lead.email_source_url,
            "姓名邮箱匹配置信度": lead.name_email_match_confidence,
        }
    )
    right.write(
        {
            "近期论文": lead.recent_publication_title,
            "PMID": lead.pmid,
            "DOI": lead.doi or "",
            "matched_keywords": lead.matched_keywords,
            "target_service_type": lead.target_service_type or "",
            "lead_score": lead.lead_score,
            "priority": lead.priority,
            "score_explanation": lead.score_explanation,
            "data_quality": lead.data_quality,
            "merge_status": lead.merge_status,
            "manual_review_required": lead.manual_review_required,
        }
    )
    st.text_area("raw_affiliation", value=lead.raw_affiliation or "", height=100)


def _render_report(st: Any, result: PubMedRunResult) -> None:
    st.write(
        {
            "Raw files": result.run_report.get("raw_files", {}),
            "Processed files": result.run_report.get("processed_files", {}),
            "Run report path": path_to_text(result.run_report_path),
        }
    )
    st.json(result.run_report)


def _render_downloads(st: Any, result: PubMedRunResult) -> None:
    _download_button_for_file(
        st,
        "下载 papers CSV",
        result.processed_paths.papers_csv,
        "text/csv",
    )
    _download_button_for_file(
        st,
        "下载 papers JSON",
        result.processed_paths.papers_json,
        "application/json",
    )
    _download_button_for_file(
        st,
        "下载 leads CSV",
        result.processed_paths.leads_csv,
        "text/csv",
    )
    _download_button_for_file(
        st,
        "下载 leads JSON",
        result.processed_paths.leads_json,
        "application/json",
    )
    _download_button_for_file(
        st,
        "下载 Run Report",
        result.run_report_path,
        "application/json",
    )


def _download_button_for_file(
    st: Any,
    label: str,
    path: Path,
    mime: str,
) -> None:
    if not path.exists():
        st.warning(f"{label} 文件不存在：{path}")
        return

    st.download_button(
        label=label,
        data=path.read_bytes(),
        file_name=path.name,
        mime=mime,
    )


def _matches_optional_filter(value: Any, selected: str | None) -> bool:
    if selected is None or selected == "" or selected == "All":
        return True
    return str(value) == selected


if __name__ == "__main__":
    main()
