<script setup>
import { Share2 } from "@lucide/vue";

defineProps({
  collapsed: {
    type: Boolean,
    default: false
  }
});
</script>

<template>
  <RouterLink class="brand" to="/" aria-label="BioLead 首页">
    <span class="brand-mark" aria-hidden="true">
      <Share2 :size="26" :stroke-width="2" />
    </span>
    <span v-if="!collapsed" class="brand-name">BioLead</span>
  </RouterLink>
</template>

<style scoped>
.brand {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  color: var(--bl-primary);
}

.brand-mark {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  place-items: center;
}

.brand-name {
  overflow: hidden;
  font-size: 25px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}
</style>
