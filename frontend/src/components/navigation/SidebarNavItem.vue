<script setup>
defineProps({
  label: {
    type: String,
    required: true
  },
  icon: {
    type: [Object, Function],
    required: true
  },
  to: {
    type: [String, Object],
    default: ""
  },
  active: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  collapsed: {
    type: Boolean,
    default: false
  }
});
</script>

<template>
  <button
    v-if="disabled"
    class="nav-item disabled"
    type="button"
    disabled
    aria-disabled="true"
    :title="collapsed ? label : '设置页面将在后续前端迁移中实现'"
  >
    <component :is="icon" :size="20" :stroke-width="1.9" aria-hidden="true" />
    <span v-if="!collapsed">{{ label }}</span>
  </button>
  <RouterLink
    v-else
    class="nav-item"
    :class="{ active }"
    :to="to"
    :title="collapsed ? label : undefined"
    :aria-label="collapsed ? label : undefined"
  >
    <component :is="icon" :size="20" :stroke-width="1.9" aria-hidden="true" />
    <span v-if="!collapsed">{{ label }}</span>
  </RouterLink>
</template>

<style scoped>
.nav-item {
  display: flex;
  width: 100%;
  height: 46px;
  align-items: center;
  gap: 14px;
  padding: 0 14px;
  border: 0;
  border-radius: var(--bl-radius-md);
  background: transparent;
  color: var(--bl-text-primary);
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
}

.nav-item:hover {
  background: var(--bl-bg-hover);
}

.nav-item.active {
  background: var(--bl-primary-soft);
  color: var(--bl-primary);
}

.nav-item.disabled {
  color: var(--bl-text-disabled);
  cursor: not-allowed;
}

.nav-item.disabled:hover {
  background: transparent;
}
</style>
