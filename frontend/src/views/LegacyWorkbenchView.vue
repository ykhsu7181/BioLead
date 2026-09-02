<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  batchGenerateEmailDrafts,
  batchReviewEmailDrafts,
  batchSendEmailDrafts,
  createJob,
  createResultPackage,
  getHealth,
  getJob,
  getJobItems,
  getLead,
  getLeadServiceMatch,
  getResultPackageDownloadUrl,
  listEmailDrafts,
  listEmailSends,
  listLeads,
  runAgent,
  runPubMedSearch
} from "../api";

const route = useRoute();

const activeView = ref("pubmed");
const apiStatus = ref("checking");
const errorMessage = ref("");
const isSearching = ref(false);
const isPackaging = ref(false);
const pubmedResult = ref(null);
const resultPackage = ref(null);
const pubmedForm = ref({
  query: "single-cell RNA sequencing cancer",
  from_date: "2026-01-01",
  to_date: "2026-12-31",
  max_results: 5,
  service_type: "single-cell RNA sequencing",
  country: ""
});

const leads = ref([]);
const selectedLeadId = ref("");
const selectedLead = ref(null);
const serviceMatch = ref(null);
const jobId = ref("");
const job = ref(null);
const jobItems = ref([]);
const emailDrafts = ref([]);
const emailSends = ref([]);
const selectedDraftIds = ref([]);
const reviewerName = ref("Reviewer");
const sendActor = ref("Reviewer");
const batchDraftStatus = ref(null);
const batchDraftTaskId = ref("");
const batchDraftMaxItems = ref(5);
const selectedDraftId = ref("");
const batchSendMode = ref("permission_check");
const agentConversationId = ref("");
const agentResult = ref(null);
const isRunningAgent = ref(false);
const pendingAgentMessage = ref("");
const pendingAgentIdempotencyKey = ref("");
const taskText = ref("帮我找 2025 年以来 single-cell cancer 的 PubMed 论文，并列出有公开邮箱的候选 PI。");
const agentMessages = ref([
  {
    role: "system",
    content: "当前页面已支持 PubMed 检索和结果展示。Agent 多轮执行仍保留为后续入口。"
  }
]);

const views = [
  { id: "pubmed", label: "PubMed 检索" },
  { id: "agent", label: "Agent 对话" },
  { id: "jobs", label: "任务进度" },
  { id: "leads", label: "客户列表" },
  { id: "detail", label: "客户详情" },
  { id: "drafts", label: "邮件草稿" }
];

watch(
  () => route.query.view,
  (view) => {
    if (typeof view === "string" && views.some((item) => item.id === view)) {
      activeView.value = view;
    }
  },
  { immediate: true }
);

const displayedPapers = computed(() => pubmedResult.value?.papers || []);
const displayedLeads = computed(() => pubmedResult.value?.leads || leads.value || []);
const selectedLeadSummary = computed(() => {
  if (!selectedLead.value) {
    return "请选择一条客户线索。";
  }
  const payload = selectedLead.value.payload || selectedLead.value;
  return `${payload.pi_full_name || selectedLead.value.lead_id} / ${payload.institution || "unknown"}`;
});

function clearError() {
  errorMessage.value = "";
}

async function refreshHealth() {
  clearError();
  try {
    const health = await getHealth();
    apiStatus.value = health.status || "ok";
  } catch (error) {
    apiStatus.value = "offline";
    errorMessage.value = error.message;
  }
}

async function submitPubMedSearch() {
  clearError();
  isSearching.value = true;
  try {
    const payload = {
      query: pubmedForm.value.query,
      from_date: pubmedForm.value.from_date,
      to_date: pubmedForm.value.to_date,
      max_results: Number(pubmedForm.value.max_results),
      service_type: pubmedForm.value.service_type || null,
      country: pubmedForm.value.country || null
    };
    pubmedResult.value = await runPubMedSearch(payload);
    resultPackage.value = null;
    leads.value = pubmedResult.value.leads || [];
    if (leads.value.length > 0) {
      selectedLeadId.value = leads.value[0].lead_id;
    }
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isSearching.value = false;
  }
}

async function generateResultPackage() {
  if (!pubmedResult.value?.task_id) {
    errorMessage.value = "Please run a PubMed search first.";
    return;
  }
  clearError();
  isPackaging.value = true;
  try {
    resultPackage.value = await createResultPackage({
      task_id: pubmedResult.value.task_id
    });
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isPackaging.value = false;
  }
}

function downloadResultPackage() {
  if (!resultPackage.value?.package_id) {
    errorMessage.value = "Please generate a result package first.";
    return;
  }
  window.open(getResultPackageDownloadUrl(resultPackage.value.package_id), "_blank", "noopener");
}

async function refreshLeads() {
  clearError();
  try {
    const data = await listLeads();
    leads.value = data.items || [];
    if (!selectedLeadId.value && leads.value.length > 0) {
      selectedLeadId.value = leads.value[0].lead_id;
    }
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function loadSelectedLead(leadId = selectedLeadId.value) {
  if (!leadId) {
    return;
  }
  clearError();
  try {
    selectedLeadId.value = leadId;
    selectedLead.value = await getLead(leadId);
    serviceMatch.value = await getLeadServiceMatch(leadId);
    activeView.value = "detail";
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function createDemoJob() {
  clearError();
  try {
    const data = await createJob({
      job_type: "BatchDraftJob",
      task_id: pubmedResult.value?.task_id || "demo-task",
      payload: { source: "vue_pubmed_demo" },
      items: [{ lead_id: selectedLeadId.value || "demo-lead", payload: { rank: 1 } }]
    });
    jobId.value = data.job_id;
    job.value = data;
    jobItems.value = [];
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function refreshJob() {
  if (!jobId.value) {
    return;
  }
  clearError();
  try {
    job.value = await getJob(jobId.value);
    const items = await getJobItems(jobId.value);
    jobItems.value = items.items || [];
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function refreshDrafts() {
  clearError();
  try {
    const data = await listEmailDrafts();
    emailDrafts.value = data.items || [];
    selectedDraftIds.value = selectedDraftIds.value.filter((draftId) =>
      emailDrafts.value.some((draft) => draft.draft_id === draftId)
    );
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function generateBatchDrafts() {
  clearError();
  try {
    batchDraftStatus.value = await batchGenerateEmailDrafts({
      task_id: batchDraftTaskId.value || pubmedResult.value?.task_id || null,
      max_items: Number(batchDraftMaxItems.value)
    });
    await refreshDrafts();
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function refreshSendLogs() {
  clearError();
  try {
    const data = await listEmailSends();
    emailSends.value = data.items || [];
  } catch (error) {
    errorMessage.value = error.message;
  }
}

function toggleDraftSelection(draftId) {
  if (selectedDraftIds.value.includes(draftId)) {
    selectedDraftIds.value = selectedDraftIds.value.filter((item) => item !== draftId);
  } else {
    selectedDraftIds.value = [...selectedDraftIds.value, draftId];
  }
}

function selectDraftForReview(draftId) {
  selectedDraftId.value = draftId;
}

async function approveSelectedDrafts() {
  if (!selectedDraftIds.value.length) {
    errorMessage.value = "请先选择邮件草稿。";
    return;
  }
  clearError();
  try {
    batchDraftStatus.value = await batchReviewEmailDrafts({
      draft_ids: selectedDraftIds.value,
      reviewer: reviewerName.value,
      decision: "approve"
    });
    await refreshDrafts();
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function runBatchSendCheck() {
  if (!selectedDraftIds.value.length) {
    errorMessage.value = "请先选择邮件草稿。";
    return;
  }
  clearError();
  try {
    batchDraftStatus.value = await batchSendEmailDrafts({
      draft_ids: selectedDraftIds.value,
      actor: sendActor.value,
      mode: batchSendMode.value,
      max_items: 5
    });
    await refreshSendLogs();
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function runAgentTask() {
  const message = taskText.value.trim();
  if (!message) {
    errorMessage.value = "请输入 Agent 任务。";
    return;
  }
  if (pendingAgentMessage.value !== message) {
    pendingAgentMessage.value = message;
    pendingAgentIdempotencyKey.value = createAgentIdempotencyKey();
  }

  clearError();
  isRunningAgent.value = true;
  agentMessages.value.push({ role: "user", content: message });
  try {
    agentResult.value = await runAgent({
      message,
      conversation_id: agentConversationId.value || null,
      max_turns: 6,
      idempotency_key: pendingAgentIdempotencyKey.value
    });
    agentConversationId.value = agentResult.value.conversation_id || "";
    agentMessages.value.push({
      role: "assistant",
      content: agentResult.value.final_answer || "Agent completed without a final answer."
    });
    pendingAgentMessage.value = "";
    pendingAgentIdempotencyKey.value = "";
    if ((agentResult.value.selected_lead_ids || []).length > 0) {
      await loadLeadsByIds(agentResult.value.selected_lead_ids);
    }
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isRunningAgent.value = false;
  }
}

function createAgentIdempotencyKey() {
  if (globalThis.crypto?.randomUUID) {
    return `agent-run-${globalThis.crypto.randomUUID()}`;
  }
  return `agent-run-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function showAgentLeads() {
  const leadIds = agentResult.value?.selected_lead_ids || [];
  if (!leadIds.length) {
    return;
  }
  clearError();
  try {
    await loadLeadsByIds(leadIds);
  } catch (error) {
    errorMessage.value = error.message;
    return;
  }
  activeView.value = "leads";
}

async function loadLeadsByIds(leadIds) {
  const data = await listLeads({ leadIds });
  leads.value = data.items || [];
  if (leads.value.length > 0) {
    selectedLeadId.value = leads.value[0].lead_id;
  }
}

onMounted(async () => {
  await refreshHealth();
  await refreshLeads();
  await refreshDrafts();
  await refreshSendLogs();
});
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">ScholarLead Agent</p>
        <h1>科研客户线索工作台</h1>
      </div>
      <div class="status-pill" :class="{ offline: apiStatus === 'offline' }">
        API {{ apiStatus }}
      </div>
    </header>

    <nav class="tabs" aria-label="Primary views">
      <button
        v-for="view in views"
        :key="view.id"
        type="button"
        :class="{ active: activeView === view.id }"
        @click="activeView = view.id"
      >
        {{ view.label }}
      </button>
    </nav>

    <p v-if="errorMessage" class="notice error">{{ errorMessage }}</p>

    <section v-if="activeView === 'pubmed'" class="panel">
      <div class="section-heading">
        <h2>PubMed 检索</h2>
        <button type="button" @click="refreshHealth">刷新 API</button>
      </div>
      <form class="form-grid" @submit.prevent="submitPubMedSearch">
        <label>
          query
          <input v-model="pubmedForm.query" required />
        </label>
        <label>
          from_date
          <input v-model="pubmedForm.from_date" type="date" required />
        </label>
        <label>
          to_date
          <input v-model="pubmedForm.to_date" type="date" required />
        </label>
        <label>
          max_results
          <input v-model.number="pubmedForm.max_results" type="number" min="1" max="20" required />
        </label>
        <label>
          service_type
          <input v-model="pubmedForm.service_type" />
        </label>
        <label>
          country
          <input v-model="pubmedForm.country" placeholder="optional" />
        </label>
        <div class="form-actions">
          <button type="submit" class="primary" :disabled="isSearching">
            {{ isSearching ? "检索中..." : "运行 PubMed 检索" }}
          </button>
        </div>
      </form>

      <div v-if="pubmedResult" class="metric-grid">
        <div><span>Task ID</span><strong>{{ pubmedResult.task_id }}</strong></div>
        <div><span>Status</span><strong>{{ pubmedResult.status }}</strong></div>
        <div><span>Papers</span><strong>{{ displayedPapers.length }}</strong></div>
        <div><span>Leads</span><strong>{{ displayedLeads.length }}</strong></div>
      </div>

      <div v-if="pubmedResult" class="result-package-panel">
        <div>
          <span>Result Package</span>
          <strong>{{ resultPackage?.package_id || "not generated" }}</strong>
          <p v-if="resultPackage" class="muted">
            customers {{ resultPackage.row_counts?.customers || 0 }},
            papers {{ resultPackage.row_counts?.papers || 0 }},
            email logs {{ resultPackage.row_counts?.email_send_logs || 0 }}
          </p>
        </div>
        <div class="button-row">
          <button type="button" @click="generateResultPackage" :disabled="isPackaging">
            {{ isPackaging ? "生成中..." : "生成结果包" }}
          </button>
          <button type="button" class="primary" :disabled="!resultPackage" @click="downloadResultPackage">
            下载 Excel
          </button>
        </div>
      </div>

      <h3>论文结果</h3>
      <table>
        <thead>
          <tr>
            <th>PMID</th>
            <th>标题</th>
            <th>期刊</th>
            <th>年份</th>
            <th>DOI</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="paper in displayedPapers" :key="paper.pmid">
            <td>{{ paper.pmid }}</td>
            <td>{{ paper.title }}</td>
            <td>{{ paper.journal }}</td>
            <td>{{ paper.publication_year || "" }}</td>
            <td>{{ paper.doi || "" }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="pubmedResult && !displayedPapers.length" class="muted">没有论文结果。</p>

      <h3>候选 PI / Leads</h3>
      <table>
        <thead>
          <tr>
            <th>Lead ID</th>
            <th>PI / 候选人</th>
            <th>邮箱</th>
            <th>机构</th>
            <th>国家</th>
            <th>分数</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="lead in displayedLeads" :key="lead.lead_id">
            <td>{{ lead.lead_id }}</td>
            <td>{{ lead.pi_full_name || lead.payload?.pi_full_name }}</td>
            <td>{{ lead.verified_email || lead.payload?.verified_email || "missing" }}</td>
            <td>{{ lead.institution || lead.payload?.institution || "" }}</td>
            <td>{{ lead.country || lead.payload?.country || "" }}</td>
            <td>{{ lead.lead_score || lead.payload?.lead_score || "" }}</td>
            <td><button type="button" @click="loadSelectedLead(lead.lead_id)">详情</button></td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="activeView === 'agent'" class="panel">
      <div class="section-heading">
        <h2>Agent 对话</h2>
        <button type="button" @click="refreshHealth">刷新 API</button>
      </div>
      <textarea v-model="taskText" rows="4" aria-label="Agent task"></textarea>
      <button type="button" class="primary" :disabled="isRunningAgent" @click="runAgentTask">
        {{ isRunningAgent ? "运行中..." : "运行 Agent" }}
      </button>
      <article v-if="agentResult" class="agent-result">
        <h3>Agent 结果</h3>
        <div class="detail-grid">
          <div><span>Conversation</span><strong>{{ agentResult.conversation_id }}</strong></div>
          <div><span>Status</span><strong>{{ agentResult.status }}</strong></div>
          <div><span>Tools</span><strong>{{ (agentResult.tools_used || []).join(", ") || "none" }}</strong></div>
          <div><span>Sources</span><strong>{{ (agentResult.sources_used || []).join(", ") || "none" }}</strong></div>
          <div><span>New Leads</span><strong>{{ agentResult.result_summary?.persisted_lead_count || 0 }}</strong></div>
        </div>
        <button
          v-if="(agentResult.selected_lead_ids || []).length > 0"
          type="button"
          @click="showAgentLeads"
        >
          查看客户列表
        </button>
      </article>
      <div class="message-list">
        <article v-for="(message, index) in agentMessages" :key="index" class="message">
          <strong>{{ message.role }}</strong>
          <p>{{ message.content }}</p>
        </article>
      </div>
    </section>

    <section v-if="activeView === 'jobs'" class="panel">
      <div class="section-heading">
        <h2>任务 / Job 进度</h2>
        <div class="button-row">
          <button type="button" @click="createDemoJob">创建演示 Job</button>
          <button type="button" @click="refreshJob">刷新 Job</button>
        </div>
      </div>
      <input v-model="jobId" placeholder="job_id" aria-label="Job ID" />
      <div v-if="job" class="metric-grid">
        <div><span>状态</span><strong>{{ job.status }}</strong></div>
        <div><span>总数</span><strong>{{ job.total_count }}</strong></div>
        <div><span>成功</span><strong>{{ job.success_count }}</strong></div>
        <div><span>失败</span><strong>{{ job.failed_count }}</strong></div>
      </div>
      <table v-if="jobItems.length">
        <thead>
          <tr>
            <th>Job Item</th>
            <th>Lead</th>
            <th>Status</th>
            <th>Attempts</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in jobItems" :key="item.job_item_id">
            <td>{{ item.job_item_id }}</td>
            <td>{{ item.lead_id }}</td>
            <td>{{ item.status }}</td>
            <td>{{ item.attempt_count }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="activeView === 'leads'" class="panel">
      <div class="section-heading">
        <h2>客户列表</h2>
        <button type="button" @click="refreshLeads">显示全部客户</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>线索 ID</th>
            <th>PI / 候选人</th>
            <th>邮箱</th>
            <th>机构</th>
            <th>国家</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="lead in leads" :key="lead.lead_id">
            <td>{{ lead.lead_id }}</td>
            <td>{{ lead.payload?.pi_full_name || lead.pi_full_name }}</td>
            <td>{{ lead.payload?.verified_email || lead.verified_email || "missing" }}</td>
            <td>{{ lead.payload?.institution || lead.institution }}</td>
            <td>{{ lead.payload?.country || lead.country }}</td>
            <td><button type="button" @click="loadSelectedLead(lead.lead_id)">查看</button></td>
          </tr>
        </tbody>
      </table>
      <p v-if="!leads.length" class="muted">数据库中暂时没有客户线索。</p>
    </section>

    <section v-if="activeView === 'detail'" class="panel">
      <div class="section-heading">
        <h2>客户详情 / Evidence</h2>
        <button type="button" @click="loadSelectedLead()">刷新详情</button>
      </div>
      <p class="lead-summary">{{ selectedLeadSummary }}</p>
      <div v-if="selectedLead" class="detail-grid">
        <div><span>Lead ID</span><strong>{{ selectedLead.lead_id }}</strong></div>
        <div><span>Email Status</span><strong>{{ selectedLead.payload?.email_status || selectedLead.email_status }}</strong></div>
        <div><span>Country</span><strong>{{ selectedLead.payload?.country || selectedLead.country }}</strong></div>
        <div><span>Score</span><strong>{{ selectedLead.payload?.lead_score || selectedLead.lead_score || "not scored" }}</strong></div>
      </div>
      <h3>Service Match</h3>
      <pre>{{ serviceMatch || { status: "not_available" } }}</pre>
      <h3>Raw Payload</h3>
      <pre>{{ selectedLead || { status: "select_a_lead" } }}</pre>
    </section>

    <section v-if="activeView === 'drafts'" class="panel">
      <div class="section-heading">
        <h2>邮件草稿 / 审核</h2>
        <div class="button-row">
          <button type="button" @click="refreshDrafts">刷新草稿</button>
          <button type="button" @click="refreshSendLogs">刷新发送记录</button>
        </div>
      </div>
      <p class="notice">这里可以批量读取草稿、审核草稿，并执行受控发送流程。默认建议先使用 permission_check。</p>
      <div class="form-grid">
        <label>
          审核人
          <input v-model="reviewerName" aria-label="Reviewer name" />
        </label>
        <label>
          发送操作人
          <input v-model="sendActor" aria-label="Send actor" />
        </label>
        <label>
          发送模式
          <select v-model="batchSendMode" aria-label="Batch send mode">
            <option value="permission_check">permission_check</option>
            <option value="test_recipient">test_recipient</option>
            <option value="real_recipient">real_recipient</option>
          </select>
        </label>
      </div>
      <div class="form-grid">
        <label>
          Batch draft task ID
          <input v-model="batchDraftTaskId" :placeholder="pubmedResult?.task_id || 'optional task_id'" />
        </label>
        <label>
          Batch draft limit
          <input v-model.number="batchDraftMaxItems" type="number" min="1" max="50" />
        </label>
        <div class="form-actions">
          <button type="button" @click="generateBatchDrafts">Generate batch drafts</button>
        </div>
      </div>
      <div class="button-row action-row">
        <button type="button" @click="approveSelectedDrafts">批准所选草稿</button>
        <button type="button" class="primary" @click="runBatchSendCheck">执行所选发送流程</button>
      </div>
      <p class="muted">已选择 {{ selectedDraftIds.length }} 封草稿，单次前端请求最多处理 5 封发送。</p>
      <table>
        <thead>
          <tr>
            <th></th>
            <th>Draft ID</th>
            <th>Lead</th>
            <th>Recipient</th>
            <th>Status</th>
            <th>Quality</th>
            <th>Subject</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="draft in emailDrafts" :key="draft.draft_id">
            <td>
              <input
                type="checkbox"
                :checked="selectedDraftIds.includes(draft.draft_id)"
                @change="toggleDraftSelection(draft.draft_id)"
                aria-label="Select draft"
              />
            </td>
            <td>{{ draft.draft_id }}</td>
            <td>{{ draft.lead_id }}</td>
            <td>{{ draft.verified_email || "missing" }}</td>
            <td>{{ draft.draft_status }}</td>
            <td>{{ draft.reviewer_workspace?.quality_report?.status || "not_checked" }}</td>
            <td>{{ draft.subject }}</td>
            <td><button type="button" @click="selectDraftForReview(draft.draft_id)">Review</button></td>
          </tr>
        </tbody>
      </table>
      <p v-if="!emailDrafts.length" class="muted">数据库中暂时没有邮件草稿。</p>
      <h3>最近状态</h3>
      <pre>{{ batchDraftStatus || { status: "no_batch_action_yet" } }}</pre>
      <article v-if="selectedDraftId" class="reviewer-workspace">
        <template v-for="draft in emailDrafts.filter((item) => item.draft_id === selectedDraftId)" :key="draft.draft_id">
          <h3>Reviewer Workspace: {{ draft.draft_id }}</h3>
          <div class="detail-grid">
            <div><span>Draft mode</span><strong>{{ draft.reviewer_workspace?.versions?.draft_mode || "legacy" }}</strong></div>
            <div><span>Quality</span><strong>{{ draft.reviewer_workspace?.quality_report?.status || "not_checked" }}</strong></div>
            <div><span>Prompt</span><strong>{{ draft.reviewer_workspace?.versions?.prompt_version || "unknown" }}</strong></div>
            <div><span>Capability status</span><strong>{{ draft.reviewer_workspace?.capability_match?.status || "not_matched" }}</strong></div>
          </div>
          <h4>Paper evidence</h4>
          <p><strong>{{ draft.reviewer_workspace?.paper_evidence?.title }}</strong></p>
          <p class="muted">{{ draft.reviewer_workspace?.paper_evidence?.abstract_preview || "No abstract evidence available." }}</p>
          <h4>Capability match</h4>
          <pre>{{ draft.reviewer_workspace?.capability_match || {} }}</pre>
          <h4>Quality report</h4>
          <pre>{{ draft.reviewer_workspace?.quality_report || {} }}</pre>
          <h4>Versions and warnings</h4>
          <pre>{{ { versions: draft.reviewer_workspace?.versions, warnings: draft.reviewer_workspace?.warnings, supersedes_draft_id: draft.payload?.supersedes_draft_id } }}</pre>
          <h4>Draft</h4>
          <p><strong>{{ draft.subject }}</strong></p>
          <pre>{{ draft.body }}</pre>
        </template>
      </article>
      <h3>发送记录</h3>
      <table>
        <thead>
          <tr>
            <th>Send ID</th>
            <th>Draft</th>
            <th>Recipient</th>
            <th>Status</th>
            <th>Provider</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in emailSends" :key="log.send_id">
            <td>{{ log.send_id }}</td>
            <td>{{ log.draft_id }}</td>
            <td>{{ log.recipient_email }}</td>
            <td>{{ log.status }}</td>
            <td>{{ log.provider || "none" }}</td>
            <td>{{ log.error_message || "" }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</template>
