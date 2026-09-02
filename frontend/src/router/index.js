import { createRouter, createWebHistory } from "vue-router";
import LegacyWorkbenchView from "../views/LegacyWorkbenchView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/workbench"
    },
    {
      path: "/workbench",
      name: "workbench",
      component: LegacyWorkbenchView
    }
  ]
});

export default router;
