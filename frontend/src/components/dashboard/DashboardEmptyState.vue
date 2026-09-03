<script setup>
defineProps({
  message: {
    type: String,
    required: true
  },
  icon: {
    type: [Object, Function],
    required: true
  },
  actionLabel: {
    type: String,
    default: ""
  },
  actionTo: {
    type: [String, Object],
    default: ""
  }
});
</script>

<template>
  <div class="empty-state">
    <component :is="icon" :size="28" :stroke-width="1.7" aria-hidden="true" />
    <p>{{ message }}</p>
    <RouterLink v-if="actionLabel && actionTo" class="empty-action" :to="actionTo">
      {{ actionLabel }}
    </RouterLink>
  </div>
</template>

<style scoped>
.empty-state {
  display: grid;
  min-height: 300px;
  place-content: center;
  justify-items: center;
  gap: 12px;
  color: var(--bl-text-muted);
}

.empty-state p {
  margin: 0;
}

.empty-action {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  padding: 0 14px;
  border: 1px solid var(--bl-primary-border);
  border-radius: var(--bl-radius-md);
  color: var(--bl-primary);
  font-weight: 600;
}

.empty-action:hover {
  background: var(--bl-primary-soft);
}
</style>
