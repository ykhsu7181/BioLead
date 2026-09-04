<script setup>
import { computed } from "vue";

const props = defineProps({
  topics: { type: Array, default: () => [] }
});

const visibleTopics = computed(() => props.topics.slice(0, 2));
const remaining = computed(() => Math.max(props.topics.length - 2, 0));
</script>

<template>
  <div v-if="topics.length" class="topic-list">
    <span v-for="topic in visibleTopics" :key="topic" class="topic-tag" :title="topic">{{ topic }}</span>
    <span v-if="remaining" class="topic-more" :title="topics.slice(2).join('、')">+{{ remaining }}</span>
  </div>
  <span v-else class="empty-value">未记录</span>
</template>

<style scoped>
.topic-list { display: flex; max-width: 250px; flex-wrap: wrap; gap: 5px; }
.topic-tag, .topic-more {
  display: inline-block;
  max-width: 150px;
  overflow: hidden;
  padding: 3px 7px;
  border: 1px solid var(--bl-primary-border);
  border-radius: var(--bl-radius-xs);
  background: var(--bl-primary-soft);
  color: var(--bl-primary-hover);
  font-size: 12px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.topic-more { border-color: var(--bl-border); background: var(--bl-bg-subtle); color: var(--bl-text-secondary); }
.empty-value { color: var(--bl-text-muted); }
</style>
