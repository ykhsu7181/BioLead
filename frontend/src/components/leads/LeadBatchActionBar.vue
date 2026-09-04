<script setup>
import { Mail, X } from "@lucide/vue";

defineProps({
  selectedCount: { type: Number, required: true },
  generating: { type: Boolean, default: false }
});

defineEmits(["generate", "clear"]);
</script>

<template>
  <section class="batch-action-bar" aria-live="polite">
    <div class="selection-summary">
      <strong>已选择 {{ selectedCount }} 位客户</strong>
      <span>只生成邮件草稿，不会发送邮件</span>
    </div>
    <button type="button" class="clear-action" @click="$emit('clear')">清空选择</button>
    <button type="button" class="generate-action" :disabled="generating" @click="$emit('generate')">
      <Mail :size="18" :stroke-width="1.9" aria-hidden="true" />
      {{ generating ? "正在生成..." : `生成邮件（${selectedCount}）` }}
    </button>
    <button type="button" class="close-action" title="取消选择" aria-label="取消选择" @click="$emit('clear')">
      <X :size="18" aria-hidden="true" />
    </button>
  </section>
</template>

<style scoped>
.batch-action-bar {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) auto auto 34px;
  min-height: 64px;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
  padding: 10px 14px;
  border: 1px solid var(--bl-primary-border);
  border-radius: var(--bl-radius-md);
  background: #f8fbff;
}
.selection-summary { display: grid; gap: 4px; }
.selection-summary strong { color: var(--bl-text-primary); }
.selection-summary span { color: var(--bl-text-secondary); font-size: 12px; }
.clear-action { padding: 8px 10px; border: 0; background: transparent; color: var(--bl-primary); cursor: pointer; }
.generate-action { display: inline-flex; min-height: 38px; align-items: center; gap: 7px; padding: 0 16px; border: 1px solid var(--bl-primary); border-radius: var(--bl-radius-sm); background: var(--bl-primary); color: white; cursor: pointer; font-weight: 600; }
.generate-action:hover:not(:disabled) { background: var(--bl-primary-hover); }
.generate-action:disabled { border-color: var(--bl-text-disabled); background: var(--bl-text-disabled); cursor: not-allowed; }
.close-action { display: grid; width: 34px; height: 34px; place-items: center; padding: 0; border: 0; border-radius: var(--bl-radius-sm); background: transparent; color: var(--bl-text-secondary); cursor: pointer; }
.close-action:hover { background: var(--bl-bg-hover); }
</style>
