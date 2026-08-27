<script setup>
import { computed, onMounted, ref } from "vue";
import {
  createJob,
  getHealth,
  getJob,
  getJobItems,
  getLead,
  getLeadServiceMatch,
  listLeads
} from "./api";

const activeView = ref("agent");
const apiStatus = ref("checking");
const errorMessage = ref("");
const leads = ref([]);
const selectedLeadId = ref("");
const selectedLead = ref(null);
const serviceMatch = ref(null);
const jobId = ref("");
const job = ref(null);
const jobItems = ref([]);
const taskText = ref("帮我找 2025 年以来 single-cell cancer 的 PubMed 论文，并列出有公开邮箱的候选 PI。");
const agentMessages = ref([
  {
    role: "system",
    content: "当前 Vue 页面是阶段 34C 骨架。Agent 执行会在后续阶段通过 FastAPI 后端接入。"
  }
]);

const views = [
  { id: "agent", label: "Agent 对话" },
  { id: "jobs", label: "任务进度" },
  { id: "leads", label: "客户列表" },
  { id: "detail", label: "客户详情" },
  { id: "drafts", label: "邮件草稿" }
];

const selectedLeadSummary = computed(() => {
  if (!selectedLead.value) {
    return "请选择一条客户线索。";
  }
  const payload = selectedLead.value.payload || {};
  return `${payload.pi_full_name || selectedLead.value.lead_id} / ${payload.institution || selectedLead.value.institution || "unknown"}`;
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
      job_type: "batch_email_draft",
      task_id: "demo-task",
      payload: { source: "vue_stage34c" },
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

function runAgentPlaceholder() {
  agentMessages.value.push({ role: "user", content: taskText.value });
  agentMessages.value.push({
    role: "assistant",
    content: "阶段 34C 只提供前端入口。正式 Agent 执行会通过后续 FastAPI 任务接口接入。"
  });
}

onMounted(async () => {
  await refreshHealth();
  await refreshLeads();
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

    <section v-if="activeView === 'agent'" class="panel">
      <div class="section-heading">
        <h2>Agent 对话</h2>
        <button type="button" @click="refreshHealth">刷新 API</button>
      </div>
      <textarea v-model="taskText" rows="4" aria-label="Agent task"></textarea>
      <button type="button" class="primary" @click="runAgentPlaceholder">运行 Agent</button>
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
        <div><span>成功</span><strong>{{ job.succeeded_count }}</strong></div>
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
        <button type="button" @click="refreshLeads">刷新客户</button>
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
      </div>
      <p class="notice">
        当前阶段只保留审核入口。批量草稿生成、审批和真实发送会在后续阶段通过后端受控流程接入。
      </p>
      <div class="draft-preview">
        <span>当前客户</span>
        <strong>{{ selectedLeadSummary }}</strong>
        <button type="button" disabled>生成草稿</button>
        <button type="button" disabled>批准发送</button>
      </div>
    </section>
  </main>
</template>
