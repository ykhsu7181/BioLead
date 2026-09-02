<script setup>
import { RouterView } from "vue-router";
import AppSidebar from "../components/navigation/AppSidebar.vue";
</script>

<template>
  <div class="app-layout">
    <AppSidebar />
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>
