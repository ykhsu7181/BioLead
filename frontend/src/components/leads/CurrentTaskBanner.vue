<script setup>
import { ChevronRight, Info } from "@lucide/vue";

defineProps({
  task: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" }
});

function formatDateTime(value) {
  if (!value) return "时间未记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false
  }).format(date);
}
</script>

<template>
  <section class="task-banner" aria-live="polite">
    <Info :size="20" :stroke-width="1.9" aria-hidden="true" />
    <div class="task-banner-copy">
      <strong v-if="loading">正在读取当前任务...</strong>
      <strong v-else-if="error">当前任务信息暂时不可用</strong>
      <template v-else-if="task">
        <strong>当前任务：{{ task.query || "未命名检索任务" }}</strong>
        <span>
          检索时间：{{ formatDateTime(task.finished_at || task.started_at) }}
          <span>检索结果：{{ task.lead_count }} 位潜在客户</span>
        </span>
      </template>
    </div>
    <RouterLink v-if="task" class="task-link" :to="{ name: 'workbench', query: { view: 'jobs' } }">
      查看任务详情 <ChevronRight :size="17" aria-hidden="true" />
    </RouterLink>
  </section>
</template>

<style scoped>
.task-banner {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 78px;
  padding: 16px 20px;
  border: 1px solid var(--bl-primary-border);
  border-radius: var(--bl-radius-md);
  background: #f8fbff;
  color: var(--bl-primary);
}
.task-banner-copy { display: grid; gap: 7px; min-width: 0; }
.task-banner-copy strong { overflow: hidden; color: var(--bl-text-primary); font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }
.task-banner-copy > span { display: flex; flex-wrap: wrap; gap: 6px 20px; color: var(--bl-text-secondary); font-size: 12px; }
.task-link { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 600; white-space: nowrap; }
.task-link:hover { color: var(--bl-primary-hover); }
</style>
