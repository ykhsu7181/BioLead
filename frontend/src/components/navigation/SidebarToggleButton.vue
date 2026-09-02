<script setup>
import { ChevronsLeft, ChevronsRight } from "@lucide/vue";

defineProps({
  collapsed: {
    type: Boolean,
    required: true
  }
});

defineEmits(["toggle"]);
</script>

<template>
  <button
    class="sidebar-toggle"
    type="button"
    :aria-label="collapsed ? '展开侧边栏' : '收起侧边栏'"
    :title="collapsed ? '展开侧边栏' : '收起侧边栏'"
    @click="$emit('toggle')"
  >
    <ChevronsRight v-if="collapsed" :size="20" :stroke-width="2" />
    <ChevronsLeft v-else :size="20" :stroke-width="2" />
  </button>
</template>

<style scoped>
.sidebar-toggle {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  padding: 0;
  place-items: center;
  border: 0;
  border-radius: var(--bl-radius-md);
  background: transparent;
  color: var(--bl-text-secondary);
  cursor: pointer;
}

.sidebar-toggle:hover {
  background: var(--bl-bg-hover);
  color: var(--bl-primary);
}
</style>
