<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Download, RotateCcw, Search, X } from "@lucide/vue";
import { generateBatchEmailDrafts } from "../api/emailDrafts";
import { getLeadFilterOptions, getLeads, getTaskSummary } from "../api/leads";
import { createTaskResultPackage, downloadResultPackage } from "../api/resultPackages";
import CurrentTaskBanner from "../components/leads/CurrentTaskBanner.vue";
import LeadBatchActionBar from "../components/leads/LeadBatchActionBar.vue";
import LeadsPagination from "../components/leads/LeadsPagination.vue";
import LeadStatusBadge from "../components/leads/LeadStatusBadge.vue";
import LeadTable from "../components/leads/LeadTable.vue";
import ResearchTopicTags from "../components/leads/ResearchTopicTags.vue";

const route = useRoute();
const router = useRouter();

const loading = ref(true);
const errorMessage = ref("");
const items = ref([]);
const result = ref({ total: 0, scope_total: 0, all_total: 0, page: 1, page_size: 20 });
const filterOptions = ref({ countries: [], research_topics: [], sources: [], email_statuses: [], contact_statuses: [] });
const taskSummary = ref(null);
const taskLoading = ref(false);
const taskError = ref("");
const previewLead = ref(null);
const searchText = ref("");
const initialized = ref(false);
const selectedLeadIds = ref([]);
const selectedLeadMap = ref(new Map());
const selectionMessage = ref("");
const generatingDrafts = ref(false);
const batchDraftResult = ref(null);
const batchDraftError = ref("");
const showSentWarning = ref(false);
const exporting = ref(false);
const exportMessage = ref("");
const exportError = ref("");
const SELECTION_LIMIT = 50;

const state = reactive({
  scope: "all",
  taskId: "",
  page: 1,
  pageSize: 20,
  query: "",
  country: "",
  research: "",
  emailStatus: "",
  contactStatus: "",
  source: "",
  manualReview: "",
  sortBy: "last_seen_at",
  sortDir: "desc"
});

const hasTaskContext = computed(() => Boolean(state.taskId));
const currentCount = computed(() => taskSummary.value?.lead_count ?? (state.scope === "current" ? result.value.scope_total : 0));
const hasFilters = computed(() => Boolean(
  state.query || state.country || state.research || state.emailStatus || state.contactStatus || state.source || state.manualReview
));
const selectedSentCount = computed(() => selectedLeadIds.value.filter(
  (leadId) => selectedLeadMap.value.get(leadId)?.contact_status === "sent"
).length);

function firstQueryValue(value, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function parsePositiveInt(value, fallback) {
  const number = Number(value);
  return Number.isInteger(number) && number > 0 ? number : fallback;
}

function applyRouteState() {
  state.taskId = firstQueryValue(route.query.task_id);
  state.scope = route.query.scope === "current" && state.taskId ? "current" : "all";
  state.page = parsePositiveInt(route.query.page, 1);
  state.pageSize = [20, 50, 100].includes(Number(route.query.page_size)) ? Number(route.query.page_size) : 20;
  state.query = firstQueryValue(route.query.query);
  state.country = firstQueryValue(route.query.country);
  state.research = firstQueryValue(route.query.research);
  state.emailStatus = firstQueryValue(route.query.email_status);
  state.contactStatus = firstQueryValue(route.query.contact_status);
  state.source = firstQueryValue(route.query.source);
  state.manualReview = firstQueryValue(route.query.manual_review);
  state.sortBy = firstQueryValue(route.query.sort_by, "last_seen_at");
  state.sortDir = route.query.sort_dir === "asc" ? "asc" : "desc";
  searchText.value = state.query;
}

function requestParams() {
  return {
    scope: state.scope,
    task_id: state.taskId,
    page: state.page,
    page_size: state.pageSize,
    query: state.query,
    country: state.country,
    research: state.research,
    email_status: state.emailStatus,
    contact_status: state.contactStatus,
    source: state.source,
    manual_review: state.manualReview,
    sort_by: state.sortBy,
    sort_dir: state.sortDir
  };
}

async function loadLeads() {
  loading.value = true;
  errorMessage.value = "";
  try {
    const data = await getLeads(requestParams());
    result.value = data;
    items.value = data.items || [];
    if (data.total > 0 && items.value.length === 0 && state.page > 1) {
      await navigate({ page: 1 });
    }
  } catch (error) {
    errorMessage.value = error.message;
    items.value = [];
  } finally {
    loading.value = false;
  }
}

async function loadTask() {
  taskSummary.value = null;
  taskError.value = "";
  if (!state.taskId) return;
  taskLoading.value = true;
  try {
    taskSummary.value = await getTaskSummary(state.taskId);
  } catch (error) {
    taskError.value = error.message;
  } finally {
    taskLoading.value = false;
  }
}

async function loadFilterOptions() {
  try {
    filterOptions.value = await getLeadFilterOptions();
  } catch (error) {
    errorMessage.value = error.message;
  }
}

async function navigate(patch = {}) {
  const next = {
    scope: state.scope,
    task_id: state.taskId,
    page: state.page,
    page_size: state.pageSize,
    query: state.query,
    country: state.country,
    research: state.research,
    email_status: state.emailStatus,
    contact_status: state.contactStatus,
    source: state.source,
    manual_review: state.manualReview,
    sort_by: state.sortBy,
    sort_dir: state.sortDir,
    ...patch
  };
  Object.keys(next).forEach((key) => {
    if (next[key] === "" || next[key] === null || next[key] === undefined || (key === "scope" && next[key] === "all") || (key === "page" && Number(next[key]) === 1) || (key === "page_size" && Number(next[key]) === 20) || (key === "sort_by" && next[key] === "last_seen_at") || (key === "sort_dir" && next[key] === "desc")) {
      delete next[key];
    }
  });
  await router.push({ name: "leads", query: next });
}

function submitSearch() {
  navigate({ query: searchText.value.trim(), page: 1 });
}

function applyFilter(key, value) {
  navigate({ [key]: value, page: 1 });
}

function resetFilters() {
  searchText.value = "";
  navigate({ query: "", country: "", research: "", email_status: "", contact_status: "", source: "", manual_review: "", page: 1 });
}

function changeSort(key) {
  const direction = state.sortBy === key && state.sortDir === "asc" ? "desc" : "asc";
  navigate({ sort_by: key, sort_dir: direction, page: 1 });
}

function clearSelection() {
  selectedLeadIds.value = [];
  selectedLeadMap.value = new Map();
  selectionMessage.value = "";
}

function toggleLeadSelection(lead, checked) {
  const ids = new Set(selectedLeadIds.value);
  const metadata = new Map(selectedLeadMap.value);
  if (checked) {
    if (ids.size >= SELECTION_LIMIT) {
      selectionMessage.value = `单次最多选择 ${SELECTION_LIMIT} 位客户。`;
      return;
    }
    ids.add(lead.lead_id);
    metadata.set(lead.lead_id, lead);
  } else {
    ids.delete(lead.lead_id);
    metadata.delete(lead.lead_id);
  }
  selectedLeadIds.value = [...ids];
  selectedLeadMap.value = metadata;
  selectionMessage.value = "";
}

function togglePageSelection(pageLeads, checked) {
  const ids = new Set(selectedLeadIds.value);
  const metadata = new Map(selectedLeadMap.value);
  if (!checked) {
    pageLeads.forEach((lead) => {
      ids.delete(lead.lead_id);
      metadata.delete(lead.lead_id);
    });
    selectionMessage.value = "";
  } else {
    let skipped = 0;
    pageLeads.forEach((lead) => {
      if (ids.has(lead.lead_id)) return;
      if (ids.size >= SELECTION_LIMIT) {
        skipped += 1;
        return;
      }
      ids.add(lead.lead_id);
      metadata.set(lead.lead_id, lead);
    });
    selectionMessage.value = skipped > 0 ? `已达到 ${SELECTION_LIMIT} 位上限，本页有 ${skipped} 位未选择。` : "";
  }
  selectedLeadIds.value = [...ids];
  selectedLeadMap.value = metadata;
}

function requestBatchDraftGeneration() {
  batchDraftError.value = "";
  batchDraftResult.value = null;
  if (selectedLeadIds.value.length === 0) return;
  if (selectedSentCount.value > 0) {
    showSentWarning.value = true;
    return;
  }
  generateSelectedDrafts();
}

async function generateSelectedDrafts() {
  showSentWarning.value = false;
  const leadIds = [...new Set(selectedLeadIds.value)];
  if (leadIds.length === 0 || leadIds.length > SELECTION_LIMIT) {
    batchDraftError.value = `请选择 1-${SELECTION_LIMIT} 位客户。`;
    return;
  }
  generatingDrafts.value = true;
  batchDraftError.value = "";
  try {
    batchDraftResult.value = await generateBatchEmailDrafts(leadIds);
  } catch (error) {
    batchDraftError.value = error.message;
  } finally {
    generatingDrafts.value = false;
  }
}

async function exportCurrentTask() {
  if (state.scope !== "current" || !state.taskId) return;
  exporting.value = true;
  exportMessage.value = "";
  exportError.value = "";
  try {
    const packageResult = await createTaskResultPackage(state.taskId);
    if (!packageResult.download_available) {
      throw new Error("结果包已创建，但 Excel 文件暂不可下载。");
    }
    downloadResultPackage(packageResult.package_id);
    exportMessage.value = `本次任务结果包已生成，共 ${packageResult.row_counts?.customers ?? 0} 位客户。`;
  } catch (error) {
    exportError.value = error.message;
  } finally {
    exporting.value = false;
  }
}

watch(
  () => route.fullPath,
  async () => {
    if (!initialized.value) return;
    const previousTask = state.taskId;
    const previousScope = state.scope;
    applyRouteState();
    if (previousTask !== state.taskId || previousScope !== state.scope) {
      clearSelection();
      batchDraftResult.value = null;
      batchDraftError.value = "";
    }
    await Promise.all([loadLeads(), previousTask !== state.taskId ? loadTask() : Promise.resolve()]);
  }
);

onMounted(async () => {
  applyRouteState();
  await Promise.all([loadFilterOptions(), loadLeads(), loadTask()]);
  initialized.value = true;
});
</script>

<template>
  <div class="leads-page">
    <header class="leads-header">
      <h1>客户</h1>
    </header>

    <div class="scope-tabs" role="tablist" aria-label="客户范围">
      <button type="button" role="tab" :aria-selected="state.scope === 'current'" :class="{ active: state.scope === 'current' }" :disabled="!hasTaskContext" @click="navigate({ scope: 'current', page: 1 })">
        本次结果 <strong>{{ currentCount.toLocaleString("zh-CN") }}</strong>
      </button>
      <button type="button" role="tab" :aria-selected="state.scope === 'all'" :class="{ active: state.scope === 'all' }" @click="navigate({ scope: 'all', page: 1 })">
        全部客户 <strong>{{ result.all_total.toLocaleString("zh-CN") }}</strong>
      </button>
    </div>

    <CurrentTaskBanner v-if="hasTaskContext" :task="taskSummary" :loading="taskLoading" :error="taskError" />

    <form class="lead-filters" aria-label="客户筛选" @submit.prevent="submitSearch">
      <label class="search-field">
        <Search :size="18" aria-hidden="true" />
        <input v-model="searchText" type="search" placeholder="搜索姓名、机构、邮箱或国家" aria-label="搜索客户" />
      </label>
      <select :value="state.country" aria-label="国家或地区" @change="applyFilter('country', $event.target.value)">
        <option value="">国家/地区</option>
        <option v-for="country in filterOptions.countries" :key="country" :value="country">{{ country }}</option>
      </select>
      <select :value="state.research" aria-label="研究领域" @change="applyFilter('research', $event.target.value)">
        <option value="">研究领域</option>
        <option v-for="topic in filterOptions.research_topics" :key="topic" :value="topic">{{ topic }}</option>
      </select>
      <select :value="state.emailStatus" aria-label="邮箱状态" @change="applyFilter('email_status', $event.target.value)">
        <option value="">邮箱状态</option>
        <option value="verified">已验证</option>
        <option value="missing">待补充</option>
        <option value="review_required">待确认</option>
      </select>
      <select :value="state.contactStatus" aria-label="联系进度" @change="applyFilter('contact_status', $event.target.value)">
        <option value="">联系进度</option>
        <option value="not_contacted">未联系</option>
        <option value="pending_review">待审核</option>
        <option value="ready_to_send">待发送</option>
        <option value="sent">已发送</option>
        <option value="rejected">已拒绝</option>
      </select>
      <select :value="state.source" aria-label="数据来源" @change="applyFilter('source', $event.target.value)">
        <option value="">来源</option>
        <option v-for="source in filterOptions.sources" :key="source" :value="source">{{ source }}</option>
      </select>
      <select :value="state.manualReview" aria-label="人工确认状态" @change="applyFilter('manual_review', $event.target.value)">
        <option value="">人工确认</option>
        <option value="true">需要确认</option>
        <option value="false">无需确认</option>
      </select>
      <button type="submit" class="filter-button primary" title="搜索" aria-label="搜索"><Search :size="18" aria-hidden="true" /></button>
      <button type="button" class="filter-button" :disabled="!hasFilters" title="重置筛选" aria-label="重置筛选" @click="resetFilters"><RotateCcw :size="18" aria-hidden="true" /></button>
      <button
        v-if="state.scope === 'current' && state.taskId"
        type="button"
        class="export-button"
        :disabled="exporting"
        @click="exportCurrentTask"
      >
        <Download :size="18" :stroke-width="1.9" aria-hidden="true" />
        {{ exporting ? "正在生成..." : "导出本次结果" }}
      </button>
    </form>

    <p v-if="selectionMessage" class="operation-notice warning" role="status">{{ selectionMessage }}</p>
    <p v-if="exportMessage" class="operation-notice success" role="status">{{ exportMessage }}</p>
    <p v-if="exportError" class="operation-notice error" role="alert">导出失败：{{ exportError }}</p>
    <div v-if="batchDraftResult" class="operation-notice success" role="status">
      <span>
        已生成 {{ batchDraftResult.success_count }} 封邮件草稿；
        {{ batchDraftResult.blocked_count + batchDraftResult.failed_count }} 位客户未生成。
      </span>
      <RouterLink :to="{ name: 'workbench', query: { view: 'drafts' } }">前往邮件草稿</RouterLink>
    </div>
    <p v-if="batchDraftError" class="operation-notice error" role="alert">草稿生成失败：{{ batchDraftError }}</p>

    <LeadBatchActionBar
      v-if="selectedLeadIds.length"
      :selected-count="selectedLeadIds.length"
      :generating="generatingDrafts"
      @generate="requestBatchDraftGeneration"
      @clear="clearSelection"
    />

    <div v-if="errorMessage" class="state-panel error" role="alert">
      <strong>客户数据加载失败</strong>
      <span>{{ errorMessage }}</span>
      <button type="button" @click="loadLeads">重新加载</button>
    </div>
    <div v-else-if="loading" class="leads-skeleton" aria-label="客户列表加载中">
      <span v-for="index in 7" :key="index"></span>
    </div>
    <div v-else-if="items.length === 0" class="state-panel">
      <strong>{{ hasFilters ? "没有符合当前筛选条件的客户" : "当前范围暂无客户" }}</strong>
      <span>调整检索条件后，这里会显示已保存的研究客户。</span>
      <button v-if="hasFilters" type="button" @click="resetFilters">清除筛选</button>
      <RouterLink v-else :to="{ name: 'workbench', query: { view: 'agent' } }">找研究客户</RouterLink>
    </div>
    <template v-else>
      <LeadTable
        :leads="items"
        :selected-lead-ids="selectedLeadIds"
        :selection-limit="SELECTION_LIMIT"
        :task-context="hasTaskContext"
        :sort-by="state.sortBy"
        :sort-dir="state.sortDir"
        @sort="changeSort"
        @preview="previewLead = $event"
        @select="toggleLeadSelection"
        @select-page="togglePageSelection"
      />
      <LeadsPagination :page="result.page" :page-size="result.page_size" :total="result.total" @page="navigate({ page: $event })" @page-size="navigate({ page_size: $event, page: 1 })" />
    </template>

    <footer class="leads-footer">© {{ new Date().getFullYear() }} BioLead</footer>

    <div v-if="previewLead" class="preview-backdrop" @click.self="previewLead = null">
      <aside class="lead-preview" role="dialog" aria-modal="true" aria-labelledby="lead-preview-title">
        <header>
          <div>
            <span>客户预览</span>
            <h2 id="lead-preview-title">{{ previewLead.pi_full_name }}</h2>
          </div>
          <button type="button" class="close-button" title="关闭" aria-label="关闭客户预览" @click="previewLead = null"><X :size="20" aria-hidden="true" /></button>
        </header>
        <dl>
          <div><dt>机构</dt><dd>{{ previewLead.institution || "未记录" }}</dd></div>
          <div><dt>国家/地区</dt><dd>{{ previewLead.country === "unknown" ? "未知" : previewLead.country }}</dd></div>
          <div><dt>邮箱</dt><dd>{{ previewLead.verified_email || "待补充" }}</dd></div>
          <div><dt>PMID</dt><dd>{{ previewLead.pmid || "未记录" }}</dd></div>
          <div><dt>最近论文</dt><dd>{{ previewLead.recent_publication_title || "未记录" }}</dd></div>
          <div><dt>发现次数</dt><dd>{{ previewLead.discovery_count }}</dd></div>
        </dl>
        <div class="preview-statuses">
          <LeadStatusBadge kind="email" :value="previewLead.email_display_status" />
          <LeadStatusBadge kind="contact" :value="previewLead.contact_status" />
        </div>
        <section>
          <h3>研究领域</h3>
          <ResearchTopicTags :topics="previewLead.research_topics" />
        </section>
      </aside>
    </div>

    <div v-if="showSentWarning" class="confirm-backdrop" @click.self="showSentWarning = false">
      <section class="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="sent-warning-title">
        <h2 id="sent-warning-title">确认再次创建草稿</h2>
        <p>所选客户中有 {{ selectedSentCount }} 位已经正式联系过。</p>
        <p>继续操作只会创建新的邮件草稿，不会自动发送。</p>
        <div class="confirm-actions">
          <button type="button" @click="showSentWarning = false">取消</button>
          <button type="button" class="primary" @click="generateSelectedDrafts">继续生成</button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.leads-page { width: 100%; max-width: var(--bl-page-max-width); margin: 0 auto; padding: 28px 32px 24px; }
.leads-header { margin-bottom: 10px; }
.leads-header h1 { margin: 0; font-size: 32px; line-height: 1.25; }
.scope-tabs { display: flex; gap: 30px; margin-bottom: 20px; border-bottom: 1px solid var(--bl-border); }
.scope-tabs button { position: relative; min-height: 52px; padding: 0 2px; border: 0; background: transparent; color: var(--bl-text-primary); cursor: pointer; font-size: 15px; }
.scope-tabs button strong { margin-left: 7px; font-size: inherit; }
.scope-tabs button.active { color: var(--bl-primary); }
.scope-tabs button.active::after { position: absolute; right: 0; bottom: -1px; left: 0; height: 2px; background: var(--bl-primary); content: ""; }
.scope-tabs button:disabled { color: var(--bl-text-disabled); cursor: not-allowed; }
.lead-filters { display: flex; flex-wrap: wrap; gap: 8px; margin: 20px 0 16px; }
.lead-filters select, .search-field { height: 40px; border: 1px solid var(--bl-border-strong); border-radius: var(--bl-radius-sm); background: var(--bl-bg-surface); }
.lead-filters select { width: 125px; min-width: 0; padding: 0 30px 0 10px; color: var(--bl-text-primary); }
.search-field { display: flex; width: min(320px, 24vw); min-width: 250px; align-items: center; gap: 8px; padding: 0 11px; color: var(--bl-text-muted); }
.search-field:focus-within { border-color: var(--bl-primary); box-shadow: var(--bl-shadow-focus); }
.search-field input { width: 100%; min-width: 0; border: 0; outline: 0; background: transparent; color: var(--bl-text-primary); }
.filter-button { display: grid; width: 38px; height: 40px; place-items: center; padding: 0; border: 1px solid var(--bl-border-strong); border-radius: var(--bl-radius-sm); background: var(--bl-bg-surface); color: var(--bl-text-secondary); cursor: pointer; }
.filter-button.primary { border-color: var(--bl-primary); background: var(--bl-primary); color: white; }
.filter-button:disabled { color: var(--bl-text-disabled); cursor: not-allowed; }
.export-button { display: inline-flex; min-height: 40px; align-items: center; gap: 7px; margin-left: auto; padding: 0 13px; border: 1px solid var(--bl-primary-border); border-radius: var(--bl-radius-sm); background: var(--bl-bg-surface); color: var(--bl-primary); cursor: pointer; font-weight: 600; }
.export-button:hover:not(:disabled) { background: var(--bl-primary-soft); }
.export-button:disabled { color: var(--bl-text-disabled); cursor: not-allowed; }
.operation-notice { display: flex; min-height: 42px; align-items: center; justify-content: space-between; gap: 16px; margin: 0 0 12px; padding: 10px 13px; border: 1px solid var(--bl-border); border-radius: var(--bl-radius-sm); background: var(--bl-bg-subtle); color: var(--bl-text-secondary); }
.operation-notice.success { border-color: #bbf0cf; background: var(--bl-success-soft); color: #166534; }
.operation-notice.warning { border-color: #fed7aa; background: var(--bl-warning-soft); color: #9a3412; }
.operation-notice.error { border-color: #fecaca; background: var(--bl-danger-soft); color: var(--bl-danger); }
.operation-notice a { color: var(--bl-primary); font-weight: 600; white-space: nowrap; }
.state-panel { display: grid; min-height: 280px; place-items: center; align-content: center; gap: 12px; border: 1px dashed var(--bl-border-strong); border-radius: var(--bl-radius-md); color: var(--bl-text-secondary); text-align: center; }
.state-panel strong { color: var(--bl-text-primary); font-size: 17px; }
.state-panel button, .state-panel a { padding: 9px 14px; border: 1px solid var(--bl-primary-border); border-radius: var(--bl-radius-sm); background: var(--bl-primary-soft); color: var(--bl-primary); cursor: pointer; }
.state-panel.error { border-style: solid; border-color: #fecaca; background: var(--bl-danger-soft); color: var(--bl-danger); }
.leads-skeleton { display: grid; gap: 1px; overflow: hidden; border: 1px solid var(--bl-border); border-radius: var(--bl-radius-md); background: var(--bl-border-soft); }
.leads-skeleton span { height: 66px; background: var(--bl-bg-subtle); }
.leads-footer { margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--bl-border-soft); color: var(--bl-text-secondary); font-size: 12px; }
.preview-backdrop { position: fixed; z-index: 20; inset: 0; display: flex; justify-content: flex-end; background: rgba(15, 23, 42, .25); }
.lead-preview { width: 480px; height: 100%; overflow-y: auto; padding: 28px; background: var(--bl-bg-surface); box-shadow: -8px 0 24px rgba(15, 23, 42, .12); }
.lead-preview header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; padding-bottom: 20px; border-bottom: 1px solid var(--bl-border); }
.lead-preview header span { color: var(--bl-text-secondary); font-size: 12px; }
.lead-preview h2 { margin: 7px 0 0; font-size: 22px; }
.close-button { display: grid; width: 36px; height: 36px; place-items: center; padding: 0; border: 0; border-radius: var(--bl-radius-sm); background: transparent; color: var(--bl-text-secondary); cursor: pointer; }
.close-button:hover { background: var(--bl-bg-hover); }
.lead-preview dl { display: grid; margin: 10px 0 20px; }
.lead-preview dl div { display: grid; grid-template-columns: 100px minmax(0, 1fr); gap: 12px; padding: 13px 0; border-bottom: 1px solid var(--bl-border-soft); }
.lead-preview dt { color: var(--bl-text-secondary); } .lead-preview dd { margin: 0; overflow-wrap: anywhere; }
.preview-statuses { display: flex; gap: 8px; margin-bottom: 24px; }
.lead-preview section h3 { margin: 0 0 10px; font-size: 14px; }
.confirm-backdrop { position: fixed; z-index: 30; inset: 0; display: grid; place-items: center; background: rgba(15, 23, 42, .28); }
.confirm-dialog { width: 430px; padding: 24px; border: 1px solid var(--bl-border); border-radius: var(--bl-radius-md); background: var(--bl-bg-surface); box-shadow: 0 18px 45px rgba(15, 23, 42, .18); }
.confirm-dialog h2 { margin: 0 0 16px; font-size: 20px; }
.confirm-dialog p { margin: 8px 0; color: var(--bl-text-secondary); line-height: 1.6; }
.confirm-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 22px; }
.confirm-actions button { min-height: 38px; padding: 0 15px; border: 1px solid var(--bl-border-strong); border-radius: var(--bl-radius-sm); background: var(--bl-bg-surface); cursor: pointer; }
.confirm-actions button.primary { border-color: var(--bl-primary); background: var(--bl-primary); color: white; }
</style>
