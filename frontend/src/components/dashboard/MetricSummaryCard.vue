<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    default: null
  },
  icon: {
    type: [Object, Function],
    required: true
  },
  tone: {
    type: String,
    default: "primary"
  },
  actionLabel: {
    type: String,
    required: true
  },
  actionTo: {
    type: [String, Object],
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
});
</script>

<template>
  <article class="metric-card">
    <div class="metric-content">
      <span class="metric-icon" :class="`tone-${tone}`" aria-hidden="true">
        <component :is="icon" :size="30" :stroke-width="1.9" />
      </span>
      <div class="metric-copy">
        <span class="metric-title">{{ title }}</span>
        <span v-if="loading" class="metric-skeleton" aria-label="加载中"></span>
        <strong v-else class="metric-value">{{ value ?? "—" }}</strong>
      </div>
    </div>
    <RouterLink class="metric-action" :to="actionTo">
      {{ actionLabel }}
      <span aria-hidden="true">›</span>
    </RouterLink>
  </article>
</template>

<style scoped>
.metric-card {
  display: flex;
  min-height: 188px;
  flex-direction: column;
  justify-content: space-between;
  padding: 28px;
  border: 1px solid var(--bl-border);
  border-radius: var(--bl-radius-md);
  background: var(--bl-bg-surface);
  box-shadow: var(--bl-shadow-card);
}

.metric-content {
  display: flex;
  align-items: center;
  gap: 22px;
}

.metric-icon {
  display: grid;
  width: 72px;
  height: 72px;
  flex: 0 0 72px;
  place-items: center;
  border-radius: 50%;
}

.tone-primary {
  background: #eff6ff;
  color: var(--bl-primary);
}

.tone-success {
  background: var(--bl-success-soft);
  color: var(--bl-success);
}

.tone-warning {
  background: var(--bl-warning-soft);
  color: var(--bl-warning);
}

.metric-copy {
  display: grid;
  min-width: 0;
  gap: 8px;
}

.metric-title {
  color: var(--bl-text-primary);
  font-size: 16px;
  font-weight: 600;
}

.metric-value {
  min-height: 50px;
  color: var(--bl-text-primary);
  font-size: 40px;
  font-weight: 700;
  line-height: 1.2;
}

.metric-skeleton {
  width: 92px;
  height: 42px;
  border-radius: var(--bl-radius-sm);
  background: var(--bl-neutral-soft);
}

.metric-action {
  display: inline-flex;
  align-self: flex-end;
  align-items: center;
  gap: 7px;
  color: var(--bl-primary);
  font-size: 13px;
  font-weight: 600;
}

.metric-action:hover {
  color: var(--bl-primary-hover);
}
</style>
