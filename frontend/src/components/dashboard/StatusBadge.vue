<script setup>
import { computed } from "vue";
import { getTaskStatus } from "../../constants/status";

const props = defineProps({
  status: {
    type: String,
    default: ""
  }
});

const statusMeta = computed(() => getTaskStatus(props.status));
</script>

<template>
  <span class="status-badge" :class="`tone-${statusMeta.tone}`">
    {{ statusMeta.label }}
  </span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  min-height: 26px;
  align-items: center;
  padding: 4px 9px;
  border-radius: var(--bl-radius-sm);
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
}

.tone-primary {
  background: var(--bl-primary-soft);
  color: var(--bl-primary);
}

.tone-neutral {
  background: var(--bl-neutral-soft);
  color: var(--bl-neutral-text);
}

.tone-danger {
  background: var(--bl-danger-soft);
  color: var(--bl-danger);
}

.tone-warning {
  background: var(--bl-warning-soft);
  color: var(--bl-warning);
}
</style>
