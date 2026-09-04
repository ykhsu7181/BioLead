<script setup>
import { ChevronLeft, ChevronRight } from "@lucide/vue";
import { computed } from "vue";

const props = defineProps({
  page: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  total: { type: Number, required: true }
});

defineEmits(["page", "page-size"]);

const pageCount = computed(() => Math.max(Math.ceil(props.total / props.pageSize), 1));
const pages = computed(() => {
  const start = Math.max(1, Math.min(props.page - 2, pageCount.value - 4));
  return Array.from({ length: Math.min(5, pageCount.value) }, (_, index) => start + index);
});
</script>

<template>
  <div class="pagination-bar">
    <span>共 {{ total.toLocaleString("zh-CN") }} 条</span>
    <div class="pagination-controls">
      <select :value="pageSize" aria-label="每页条数" @change="$emit('page-size', Number($event.target.value))">
        <option :value="20">20 条/页</option>
        <option :value="50">50 条/页</option>
        <option :value="100">100 条/页</option>
      </select>
      <button type="button" class="page-button" :disabled="page <= 1" aria-label="上一页" @click="$emit('page', page - 1)">
        <ChevronLeft :size="17" aria-hidden="true" />
      </button>
      <button v-for="number in pages" :key="number" type="button" class="page-button" :class="{ active: number === page }" :aria-current="number === page ? 'page' : undefined" @click="$emit('page', number)">{{ number }}</button>
      <button type="button" class="page-button" :disabled="page >= pageCount" aria-label="下一页" @click="$emit('page', page + 1)">
        <ChevronRight :size="17" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.pagination-bar { display: flex; min-height: 52px; align-items: center; justify-content: space-between; gap: 20px; color: var(--bl-text-secondary); font-size: 13px; }
.pagination-controls { display: flex; align-items: center; gap: 7px; }
.pagination-controls select { height: 34px; padding: 0 30px 0 10px; border: 1px solid var(--bl-border-strong); border-radius: var(--bl-radius-sm); background: var(--bl-bg-surface); color: var(--bl-text-primary); }
.page-button { display: grid; min-width: 34px; height: 34px; place-items: center; padding: 0 8px; border: 1px solid var(--bl-border); border-radius: var(--bl-radius-sm); background: var(--bl-bg-surface); color: var(--bl-text-primary); cursor: pointer; }
.page-button:hover:not(:disabled), .page-button.active { border-color: var(--bl-primary); color: var(--bl-primary); }
.page-button.active { background: var(--bl-primary-soft); font-weight: 600; }
.page-button:disabled { color: var(--bl-text-disabled); cursor: not-allowed; }
</style>
