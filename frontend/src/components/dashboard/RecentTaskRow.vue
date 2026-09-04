<script setup>
import { Search } from "@lucide/vue";
import StatusBadge from "./StatusBadge.vue";

const props = defineProps({
  task: {
    type: Object,
    required: true
  }
});

function formatDateTime(value) {
  if (!value) {
    return "时间未记录";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  }).format(date);
}

function formatTime(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  }).format(date);
}
</script>

<template>
  <RouterLink
    class="recent-task-row"
    :to="{ name: 'leads', query: { scope: 'current', task_id: props.task.task_id } }"
    :aria-label="`查看任务 ${props.task.query || '未命名检索任务'} 的客户`"
  >
    <span class="task-icon" aria-hidden="true">
      <Search :size="20" :stroke-width="1.9" />
    </span>
    <div class="task-copy">
      <h3>{{ props.task.query || "未命名检索任务" }}</h3>
      <p>
        检索时间：{{ formatDateTime(props.task.finished_at || props.task.started_at) }}
        <span>结果：{{ props.task.lead_count }} 位潜在客户</span>
      </p>
    </div>
    <div class="task-status">
      <StatusBadge :status="props.task.status" />
      <time>{{ formatTime(props.task.finished_at || props.task.started_at) }}</time>
    </div>
  </RouterLink>
</template>

<style scoped>
.recent-task-row {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  padding: 18px 0;
  border-bottom: 1px solid var(--bl-border-soft);
}

.recent-task-row:last-child {
  border-bottom: 0;
}

.recent-task-row:hover .task-copy h3 {
  color: var(--bl-primary);
}

.task-icon {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 50%;
  background: #eff6ff;
  color: var(--bl-primary);
}

.task-copy {
  min-width: 0;
}

.task-copy h3 {
  overflow: hidden;
  margin: 0 0 7px;
  color: var(--bl-text-primary);
  font-size: 15px;
  font-weight: 600;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-copy p {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  margin: 0;
  color: var(--bl-text-secondary);
  font-size: 13px;
}

.task-status {
  display: grid;
  min-width: 76px;
  justify-items: end;
  gap: 8px;
}

.task-status time {
  min-height: 16px;
  color: var(--bl-text-secondary);
  font-size: 12px;
}
</style>
