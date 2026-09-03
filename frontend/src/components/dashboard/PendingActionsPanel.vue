<script setup>
import { Inbox } from "@lucide/vue";
import DashboardEmptyState from "./DashboardEmptyState.vue";
import PendingActionRow from "./PendingActionRow.vue";

defineProps({
  actions: {
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
  <section class="dashboard-panel" aria-labelledby="pending-actions-title">
    <header class="panel-header">
      <h2 id="pending-actions-title">待处理事项</h2>
    </header>
    <div v-if="loading" class="panel-loading" aria-label="待处理事项加载中">
      <span v-for="index in 3" :key="index"></span>
    </div>
    <div v-else-if="actions.length" class="action-list">
      <PendingActionRow
        v-for="action in actions"
        :key="action.id"
        v-bind="action"
      />
    </div>
    <DashboardEmptyState v-else message="当前没有需要处理的事项" :icon="Inbox" />
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
  height: 72px;
  border-radius: var(--bl-radius-sm);
  background: var(--bl-bg-subtle);
}

.action-list {
  min-width: 0;
}
</style>
