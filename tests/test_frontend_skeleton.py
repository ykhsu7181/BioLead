import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def test_vue_frontend_skeleton_files_exist() -> None:
    expected = [
        "package.json",
        "index.html",
        "vite.config.js",
        "src/main.js",
        "src/App.vue",
        "src/api.js",
        "src/router/index.js",
        "src/views/LegacyWorkbenchView.vue",
        "src/styles.css",
        "README.md",
    ]

    for relative_path in expected:
        assert (FRONTEND / relative_path).is_file()


def test_vue_frontend_package_uses_vite_and_vue() -> None:
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))

    assert package["private"] is True
    assert "dev" in package["scripts"]
    assert "build" in package["scripts"]
    assert "vue" in package["dependencies"]
    assert "vue-router" in package["dependencies"]
    assert "vite" in package["dependencies"]


def test_frontend_keeps_secrets_and_external_services_out_of_browser_code() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (FRONTEND / "src").rglob("*")
        if path.is_file()
    )

    forbidden_terms = [
        "OPENAI_API_KEY",
        "SMTP_PASSWORD",
        "NCBI_API_KEY",
        "api.openai.com",
        "api.openalex.org",
        "eutils.ncbi.nlm.nih.gov",
        "smtp.",
        "sqlite",
    ]

    for term in forbidden_terms:
        assert term not in source


def test_frontend_exposes_batch_email_review_and_send_controls() -> None:
    app = (FRONTEND / "src" / "views" / "LegacyWorkbenchView.vue").read_text(
        encoding="utf-8"
    )
    api = (FRONTEND / "src" / "api.js").read_text(encoding="utf-8")

    assert "/api/email-drafts/batch-review" in api
    assert "/api/email-sends/batch-send" in api
    assert "批准所选草稿" in app
    assert "permission_check" in app
    assert "/api/email-drafts/batch-generate" in api
    assert "Generate batch drafts" in app
    assert "Reviewer Workspace" in app


def test_frontend_exposes_pubmed_search_and_result_tables() -> None:
    app = (FRONTEND / "src" / "views" / "LegacyWorkbenchView.vue").read_text(
        encoding="utf-8"
    )
    api = (FRONTEND / "src" / "api.js").read_text(encoding="utf-8")

    assert "/api/pubmed/search" in api
    assert "PubMed 检索" in app
    assert "运行 PubMed 检索" in app
    assert "论文结果" in app
    assert "候选 PI / Leads" in app


def test_frontend_exposes_result_package_generation_and_download() -> None:
    app = (FRONTEND / "src" / "views" / "LegacyWorkbenchView.vue").read_text(
        encoding="utf-8"
    )
    api = (FRONTEND / "src" / "api.js").read_text(encoding="utf-8")

    assert "/api/result-packages" in api
    assert "/download" in api
    assert "生成结果包" in app
    assert "下载 Excel" in app
    assert "generateResultPackage" in app


def test_frontend_agent_dialog_uses_the_real_agent_api() -> None:
    app = (FRONTEND / "src" / "views" / "LegacyWorkbenchView.vue").read_text(
        encoding="utf-8"
    )
    api = (FRONTEND / "src" / "api.js").read_text(encoding="utf-8")

    assert "/api/agent/run" in api
    assert "runAgentTask" in app
    assert "runAgentPlaceholder" not in app
    assert "agentConversationId" in app
    assert "pendingAgentIdempotencyKey" in app
    assert "selected_lead_ids" in app
    assert "showAgentLeads" in app


def test_frontend_routes_root_and_legacy_workbench() -> None:
    app = (FRONTEND / "src" / "App.vue").read_text(encoding="utf-8")
    main = (FRONTEND / "src" / "main.js").read_text(encoding="utf-8")
    router = (FRONTEND / "src" / "router" / "index.js").read_text(encoding="utf-8")
    legacy = (FRONTEND / "src" / "views" / "LegacyWorkbenchView.vue").read_text(
        encoding="utf-8"
    )

    assert "RouterView" in app
    assert "createApp(App).use(router)" in main
    assert 'path: "/"' in router
    assert 'redirect: "/workbench"' in router
    assert 'path: "/workbench"' in router
    assert "LegacyWorkbenchView" in router
    assert "route.query.view" in legacy
