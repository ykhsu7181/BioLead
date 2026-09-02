<script setup>
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ClipboardCheck, House, Mail, Plus, Settings, UserRound } from "@lucide/vue";
import BioLeadLogo from "../branding/BioLeadLogo.vue";
import SidebarNavItem from "./SidebarNavItem.vue";
import SidebarToggleButton from "./SidebarToggleButton.vue";

const STORAGE_KEY = "biolead.sidebar.collapsed";
const route = useRoute();
const collapsed = ref(globalThis.localStorage?.getItem(STORAGE_KEY) === "true");

const navItems = [
  { label: "首页", icon: House, to: { name: "dashboard" }, view: "dashboard" },
  { label: "客户", icon: UserRound, to: { name: "workbench", query: { view: "leads" } }, view: "leads" },
  { label: "邮件", icon: Mail, to: { name: "workbench", query: { view: "drafts" } }, view: "drafts" },
  { label: "任务", icon: ClipboardCheck, to: { name: "workbench", query: { view: "jobs" } }, view: "jobs" },
  { label: "设置", icon: Settings, disabled: true, view: "settings" }
];

const sidebarLabel = computed(() => (collapsed.value ? "BioLead 导航" : "主导航"));

function isActive(item) {
  if (item.view === "dashboard") {
    return route.name === "dashboard";
  }
  return route.name === "workbench" && route.query.view === item.view;
}

function toggleSidebar() {
  collapsed.value = !collapsed.value;
}

watch(collapsed, (value) => {
  globalThis.localStorage?.setItem(STORAGE_KEY, String(value));
});
</script>

<template>
  <aside class="app-sidebar" :class="{ collapsed }" :aria-label="sidebarLabel">
    <div class="sidebar-header">
      <BioLeadLogo :collapsed="collapsed" />
      <SidebarToggleButton :collapsed="collapsed" @toggle="toggleSidebar" />
    </div>

    <RouterLink
      class="find-button"
      :class="{ collapsed }"
      :to="{ name: 'workbench', query: { view: 'agent' } }"
      :title="collapsed ? '找研究客户' : undefined"
      :aria-label="collapsed ? '找研究客户' : undefined"
    >
      <Plus :size="21" :stroke-width="2" aria-hidden="true" />
      <span v-if="!collapsed">找研究客户</span>
    </RouterLink>

    <nav class="sidebar-nav" aria-label="BioLead 页面">
      <SidebarNavItem
        v-for="item in navItems"
        :key="item.view"
        v-bind="item"
        :active="isActive(item)"
        :collapsed="collapsed"
      />
    </nav>

    <div class="sidebar-footer">
      <SidebarToggleButton :collapsed="collapsed" @toggle="toggleSidebar" />
      <span v-if="!collapsed">收起菜单</span>
    </div>
  </aside>
</template>

<style scoped>
.app-sidebar {
  position: sticky;
  top: 0;
  display: flex;
  width: var(--bl-sidebar-expanded);
  height: 100vh;
  flex: 0 0 var(--bl-sidebar-expanded);
  flex-direction: column;
  padding: 22px 18px 18px;
  border-right: 1px solid var(--bl-border-soft);
  background: var(--bl-bg-sidebar);
  overflow: hidden;
  transition: width 180ms ease, flex-basis 180ms ease;
}

.app-sidebar.collapsed {
  width: var(--bl-sidebar-collapsed);
  flex-basis: var(--bl-sidebar-collapsed);
  padding-inline: 10px;
}

.sidebar-header {
  display: flex;
  min-height: 40px;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.collapsed .sidebar-header {
  justify-content: center;
}

.collapsed .sidebar-header > :last-child {
  display: none;
}

.find-button {
  display: flex;
  width: 100%;
  height: 50px;
  flex: 0 0 50px;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 28px;
  border-radius: var(--bl-radius-md);
  background: var(--bl-primary);
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
}

.find-button:hover {
  background: var(--bl-primary-hover);
}

.find-button.collapsed {
  padding: 0;
}

.sidebar-nav {
  display: grid;
  gap: 8px;
  margin-top: 28px;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 18px;
  border-top: 1px solid var(--bl-border-soft);
  color: var(--bl-text-secondary);
  white-space: nowrap;
}

.collapsed .sidebar-footer {
  justify-content: center;
}
</style>
