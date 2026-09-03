<script setup>
import { ChevronRight } from "@lucide/vue";

defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    required: true
  },
  count: {
    type: Number,
    required: true
  },
  icon: {
    type: [Object, Function],
    required: true
  },
  tone: {
    type: String,
    required: true
  },
  to: {
    type: [String, Object],
    required: true
  }
});
</script>

<template>
  <RouterLink class="pending-action-row" :to="to">
    <span class="action-icon" :class="`tone-${tone}`" aria-hidden="true">
      <component :is="icon" :size="22" :stroke-width="1.9" />
    </span>
    <span class="action-copy">
      <strong>{{ title }}</strong>
      <span>{{ description }}</span>
    </span>
    <strong class="action-count">{{ count }}</strong>
    <ChevronRight class="action-chevron" :size="20" :stroke-width="1.9" aria-hidden="true" />
  </RouterLink>
</template>

<style scoped>
.pending-action-row {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto 20px;
  min-height: 100px;
  align-items: center;
  gap: 14px;
  border-bottom: 1px solid var(--bl-border-soft);
}

.pending-action-row:last-child {
  border-bottom: 0;
}

.pending-action-row:hover .action-copy strong,
.pending-action-row:hover .action-chevron {
  color: var(--bl-primary);
}

.action-icon {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 50%;
}

.tone-success {
  background: var(--bl-success-soft);
  color: var(--bl-success);
}

.tone-warning {
  background: var(--bl-warning-soft);
  color: var(--bl-warning);
}

.tone-purple {
  background: var(--bl-purple-soft);
  color: var(--bl-purple);
}

.action-copy {
  display: grid;
  min-width: 0;
  gap: 7px;
}

.action-copy strong {
  color: var(--bl-text-primary);
  font-size: 15px;
  font-weight: 600;
}

.action-copy span {
  color: var(--bl-text-secondary);
  font-size: 13px;
}

.action-count {
  color: var(--bl-primary);
  font-size: 20px;
  font-weight: 600;
}

.action-chevron {
  color: var(--bl-text-muted);
}
</style>
