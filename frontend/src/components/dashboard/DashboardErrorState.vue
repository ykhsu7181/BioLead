<script setup>
import { CircleAlert, RefreshCw } from "@lucide/vue";

defineEmits(["retry"]);
</script>

<template>
  <div class="error-state" role="alert">
    <CircleAlert :size="20" :stroke-width="1.9" aria-hidden="true" />
    <span>暂时无法加载首页数据</span>
    <button type="button" @click="$emit('retry')">
      <RefreshCw :size="16" :stroke-width="2" aria-hidden="true" />
      重新加载
    </button>
  </div>
</template>

<style scoped>
.error-state {
  display: flex;
  min-height: 52px;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding: 10px 14px;
  border: 1px solid #fecaca;
  border-radius: var(--bl-radius-md);
  background: var(--bl-danger-soft);
  color: var(--bl-danger);
}

.error-state button {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  padding: 0 11px;
  border: 1px solid #fecaca;
  border-radius: var(--bl-radius-sm);
  background: #ffffff;
  color: var(--bl-danger);
  cursor: pointer;
}
</style>
