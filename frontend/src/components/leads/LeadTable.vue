<script setup>
import { ChevronDown, ChevronUp, ExternalLink } from "@lucide/vue";
import { computed } from "vue";
import LeadStatusBadge from "./LeadStatusBadge.vue";
import ResearchTopicTags from "./ResearchTopicTags.vue";

const props = defineProps({
  leads: { type: Array, default: () => [] },
  selectedLeadIds: { type: Array, default: () => [] },
  selectionLimit: { type: Number, default: 50 },
  taskContext: { type: Boolean, default: false },
  sortBy: { type: String, required: true },
  sortDir: { type: String, required: true }
});

const emit = defineEmits(["sort", "preview", "select", "select-page"]);

const selectedSet = computed(() => new Set(props.selectedLeadIds));
const selectedOnPage = computed(() => props.leads.filter((lead) => selectedSet.value.has(lead.lead_id)).length);
const allOnPageSelected = computed(() => props.leads.length > 0 && selectedOnPage.value === props.leads.length);

function togglePage(event) {
  emit("select-page", props.leads, event.target.checked);
}

function toggleLead(lead, event) {
  emit("select", lead, event.target.checked);
}

const sortableColumns = {
  name: "姓名",
  institution: "机构",
  country: "国家/地区",
  email_status: "邮箱状态",
  contact_status: "联系进度",
  last_seen_at: "来源 / 发现时间"
};

function sourceLabel(source) {
  const labels = { pubmed: "PubMed", openalex: "OpenAlex", crossref: "Crossref", legacy: "历史数据" };
  return labels[source] || source || "未记录";
}

function formatDate(value) {
  if (!value) return "时间未记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" }).format(date);
}
</script>

<template>
  <div class="lead-table-wrap">
    <table class="lead-table">
      <thead>
        <tr>
          <th class="column-select">
            <input
              type="checkbox"
              :checked="allOnPageSelected"
              :aria-label="allOnPageSelected ? '取消选择当前页' : '选择当前页'"
              @change="togglePage"
            />
          </th>
          <th v-for="(label, key) in sortableColumns" :key="key" :class="`column-${key}`">
            <button type="button" class="sort-button" @click="$emit('sort', key)">
              {{ label }}
              <ChevronUp v-if="sortBy === key && sortDir === 'asc'" :size="14" aria-hidden="true" />
              <ChevronDown v-else :size="14" :class="{ muted: sortBy !== key }" aria-hidden="true" />
            </button>
          </th>
          <th class="column-research">研究领域</th>
          <th class="column-action">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="lead in leads" :key="lead.lead_id">
          <td class="column-select">
            <input
              type="checkbox"
              :checked="selectedSet.has(lead.lead_id)"
              :disabled="selectedLeadIds.length >= selectionLimit && !selectedSet.has(lead.lead_id)"
              :aria-label="`选择客户 ${lead.pi_full_name}`"
              @change="toggleLead(lead, $event)"
            />
          </td>
          <td>
            <button type="button" class="lead-name" @click="$emit('preview', lead)">{{ lead.pi_full_name }}</button>
            <span v-if="lead.verified_email" class="lead-email">{{ lead.verified_email }}</span>
            <span v-else class="lead-email missing">邮箱待补充</span>
            <span v-if="taskContext && lead.current_task_match" class="current-match">本次命中</span>
          </td>
          <td>{{ lead.institution || "未记录" }}</td>
          <td>{{ lead.country === "unknown" ? "未知" : lead.country }}</td>
          <td><LeadStatusBadge kind="email" :value="lead.email_display_status" /></td>
          <td><LeadStatusBadge kind="contact" :value="lead.contact_status" /></td>
          <td>
            <div class="source-cell">
              <span>{{ sourceLabel(lead.matched_source || lead.latest_source) }}</span>
              <time>{{ formatDate(lead.last_seen_at) }}</time>
            </div>
          </td>
          <td><ResearchTopicTags :topics="lead.research_topics" /></td>
          <td>
            <button type="button" class="icon-action" title="查看客户详情" aria-label="查看客户详情" @click="$emit('preview', lead)">
              <ExternalLink :size="17" :stroke-width="1.9" aria-hidden="true" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.lead-table-wrap { width: 100%; overflow-x: auto; border: 1px solid var(--bl-border); border-radius: var(--bl-radius-md); }
.lead-table { width: 100%; min-width: 1240px; border-collapse: collapse; table-layout: fixed; }
.lead-table th, .lead-table td { padding: 14px 12px; border-bottom: 1px solid var(--bl-border-soft); text-align: left; vertical-align: middle; }
.lead-table th { background: var(--bl-bg-subtle); color: var(--bl-text-secondary); font-size: 12px; font-weight: 600; }
.lead-table tbody tr:last-child td { border-bottom: 0; }
.lead-table tbody tr:hover { background: var(--bl-bg-hover); }
.column-select { width: 46px; text-align: center !important; }
.column-select input { width: 16px; height: 16px; accent-color: var(--bl-primary); cursor: pointer; }
.column-select input:disabled { cursor: not-allowed; }
.column-name { width: 220px; } .column-institution { width: 230px; } .column-country { width: 120px; }
.column-email_status { width: 110px; } .column-contact_status { width: 110px; } .column-last_seen_at { width: 145px; }
.column-research { width: 210px; } .column-action { width: 60px; }
.sort-button { display: inline-flex; min-height: 26px; align-items: center; gap: 4px; padding: 0; border: 0; background: transparent; color: inherit; cursor: pointer; font-weight: inherit; }
.sort-button:hover { color: var(--bl-primary); } .sort-button .muted { color: var(--bl-text-muted); }
.lead-name { display: block; max-width: 100%; overflow: hidden; padding: 0; border: 0; background: transparent; color: var(--bl-primary); cursor: pointer; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.lead-name:hover { color: var(--bl-primary-hover); text-decoration: underline; }
.lead-email { display: block; max-width: 100%; overflow: hidden; margin-top: 5px; color: var(--bl-text-secondary); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.lead-email.missing { color: var(--bl-text-muted); }
.current-match { display: inline-block; margin-top: 7px; padding: 2px 6px; border-radius: var(--bl-radius-xs); background: var(--bl-primary-soft); color: var(--bl-primary); font-size: 11px; }
.source-cell { display: grid; gap: 5px; } .source-cell time { color: var(--bl-text-secondary); font-size: 12px; }
.icon-action { display: grid; width: 34px; height: 34px; place-items: center; padding: 0; border: 1px solid var(--bl-border-strong); border-radius: var(--bl-radius-sm); background: var(--bl-bg-surface); color: var(--bl-text-secondary); cursor: pointer; }
.icon-action:hover { border-color: var(--bl-primary-border); color: var(--bl-primary); }
</style>
