import { createRouter, createWebHistory } from "vue-router";
import AppLayout from "../layouts/AppLayout.vue";
import DashboardView from "../views/DashboardView.vue";
import LegacyWorkbenchView from "../views/LegacyWorkbenchView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      component: AppLayout,
      children: [
        {
          path: "",
          name: "dashboard",
          component: DashboardView
        }
      ]
    },
    {
      path: "/workbench",
      name: "workbench",
      component: LegacyWorkbenchView
    }
  ]
});

export default router;
