<script setup>
import { computed } from "vue";
import { getLeadStatus } from "../../constants/leadStatus";

const props = defineProps({
  kind: { type: String, required: true },
  value: { type: String, default: "" }
});

const status = computed(() => getLeadStatus(props.kind, props.value));
</script>

<template>
  <span class="lead-status" :class="`tone-${status.tone}`">{{ status.label }}</span>
</template>

<style scoped>
.lead-status {
  display: inline-flex;
  min-height: 26px;
  align-items: center;
  padding: 3px 9px;
  border: 1px solid var(--bl-border);
  border-radius: var(--bl-radius-xs);
  background: var(--bl-neutral-soft);
  color: var(--bl-neutral-text);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.tone-success { border-color: #bbf0cf; background: var(--bl-success-soft); color: var(--bl-success); }
.tone-warning { border-color: #fed7aa; background: var(--bl-warning-soft); color: #b45309; }
.tone-primary { border-color: var(--bl-primary-border); background: var(--bl-primary-soft); color: var(--bl-primary); }
.tone-danger { border-color: #fecaca; background: var(--bl-danger-soft); color: var(--bl-danger); }
</style>
