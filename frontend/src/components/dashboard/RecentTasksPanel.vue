<script setup>
import { ClipboardList } from "@lucide/vue";
import DashboardEmptyState from "./DashboardEmptyState.vue";
import RecentTaskRow from "./RecentTaskRow.vue";

defineProps({
  tasks: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
});
</script>

<template>
  <section class="dashboard-panel" aria-labelledby="recent-tasks-title">
    <header class="panel-header">
      <h2 id="recent-tasks-title">最近任务</h2>
    </header>
    <div v-if="loading" class="panel-loading" aria-label="最近任务加载中">
      <span v-for="index in 4" :key="index"></span>
    </div>
    <div v-else-if="tasks.length" class="task-list">
      <RecentTaskRow v-for="task in tasks" :key="task.task_id" :task="task" />
    </div>
    <DashboardEmptyState
      v-else
      message="暂无客户检索任务"
      :icon="ClipboardList"
      action-label="找研究客户"
      :action-to="{ name: 'workbench', query: { view: 'agent' } }"
    />
  </section>
</template>

<style scoped>
.dashboard-panel {
  min-height: 430px;
  padding: 26px 28px;
  border: 1px solid var(--bl-border);
  border-radius: var(--bl-radius-md);
  background: var(--bl-bg-surface);
  box-shadow: var(--bl-shadow-card);
}

.panel-header {
  padding-bottom: 20px;
  border-bottom: 1px solid var(--bl-border-soft);
}

.panel-header h2 {
  margin: 0;
  font-size: 21px;
  line-height: 1.3;
}

.panel-loading {
  display: grid;
  gap: 14px;
  padding-top: 24px;
}

.panel-loading span {
  height: 58px;
  border-radius: var(--bl-radius-sm);
  background: var(--bl-bg-subtle);
}

.task-list {
  min-width: 0;
}
</style>
