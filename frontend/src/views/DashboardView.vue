<script setup>
import { Mail, Send, UsersRound } from "@lucide/vue";
import MetricSummaryCard from "../components/dashboard/MetricSummaryCard.vue";
import PendingActionsPanel from "../components/dashboard/PendingActionsPanel.vue";
import RecentTasksPanel from "../components/dashboard/RecentTasksPanel.vue";

const emailRoute = { name: "workbench", query: { view: "drafts" } };
</script>

<template>
  <div class="dashboard-page">
    <header class="dashboard-header">
      <h1 class="dashboard-title">首页</h1>
    </header>

    <section class="dashboard-metrics" aria-label="业务概览">
      <MetricSummaryCard
        title="潜在客户"
        :icon="UsersRound"
        tone="primary"
        action-label="查看客户"
        :action-to="{ name: 'workbench', query: { view: 'leads' } }"
      />
      <MetricSummaryCard
        title="待审核邮件"
        :icon="Mail"
        tone="success"
        action-label="查看邮件"
        :action-to="emailRoute"
      />
      <MetricSummaryCard
        title="待发送邮件"
        :icon="Send"
        tone="warning"
        action-label="查看邮件"
        :action-to="emailRoute"
      />
    </section>

    <section class="dashboard-body" aria-label="任务和待处理事项">
      <RecentTasksPanel />
      <PendingActionsPanel />
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
