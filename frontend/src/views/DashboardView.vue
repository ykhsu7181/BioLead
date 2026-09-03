<script setup>
import { computed, onMounted, ref } from "vue";
import { Mail, Send, UserRoundCheck, UsersRound } from "@lucide/vue";
import { getDashboardSummary } from "../api/dashboard";
import DashboardErrorState from "../components/dashboard/DashboardErrorState.vue";
import MetricSummaryCard from "../components/dashboard/MetricSummaryCard.vue";
import PendingActionsPanel from "../components/dashboard/PendingActionsPanel.vue";
import RecentTasksPanel from "../components/dashboard/RecentTasksPanel.vue";

const emailRoute = { name: "workbench", query: { view: "drafts" } };
const loading = ref(true);
const hasError = ref(false);
const summary = ref(null);

const pendingActions = computed(() => {
  if (!summary.value) {
    return [];
  }
  return [
    {
      id: "pending-review",
      title: "待审核邮件",
      description: `有 ${summary.value.pending_review_count} 封邮件等待审核`,
      count: summary.value.pending_review_count,
      icon: Mail,
      tone: "success",
      to: emailRoute
    },
    {
      id: "ready-to-send",
      title: "待发送邮件",
      description: `有 ${summary.value.ready_to_send_count} 封邮件已审核，等待发送`,
      count: summary.value.ready_to_send_count,
      icon: Send,
      tone: "warning",
      to: emailRoute
    },
    {
      id: "manual-review",
      title: "待人工确认客户",
      description: `有 ${summary.value.manual_review_lead_count} 位客户需要人工确认`,
      count: summary.value.manual_review_lead_count,
      icon: UserRoundCheck,
      tone: "purple",
      to: { name: "workbench", query: { view: "leads" } }
    }
  ].filter((action) => action.count > 0);
});

async function loadSummary() {
  loading.value = true;
  hasError.value = false;
  try {
    summary.value = await getDashboardSummary();
  } catch {
    hasError.value = true;
    summary.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(loadSummary);
</script>

<template>
  <div class="dashboard-page">
    <header class="dashboard-header">
      <h1 class="dashboard-title">首页</h1>
    </header>

    <DashboardErrorState v-if="hasError" @retry="loadSummary" />

    <section class="dashboard-metrics" aria-label="业务概览">
      <MetricSummaryCard
        title="潜在客户"
        :value="summary?.lead_count"
        :icon="UsersRound"
        tone="primary"
        action-label="查看客户"
        :action-to="{ name: 'workbench', query: { view: 'leads' } }"
        :loading="loading"
      />
      <MetricSummaryCard
        title="待审核邮件"
        :value="summary?.pending_review_count"
        :icon="Mail"
        tone="success"
        action-label="查看邮件"
        :action-to="emailRoute"
        :loading="loading"
      />
      <MetricSummaryCard
        title="待发送邮件"
        :value="summary?.ready_to_send_count"
        :icon="Send"
        tone="warning"
        action-label="查看邮件"
        :action-to="emailRoute"
        :loading="loading"
      />
    </section>

    <section class="dashboard-body" aria-label="任务和待处理事项">
      <RecentTasksPanel :tasks="summary?.recent_tasks || []" :loading="loading" />
      <PendingActionsPanel :actions="pendingActions" :loading="loading" />
    </section>

    <footer class="dashboard-footer">
      <span>© {{ new Date().getFullYear() }} BioLead</span>
    </footer>
  </div>
</template>

<style scoped>
.dashboard-footer {
  margin-top: 24px;
  padding-top: 22px;
  border-top: 1px solid var(--bl-border-soft);
  color: var(--bl-text-secondary);
  font-size: 13px;
}
</style>
