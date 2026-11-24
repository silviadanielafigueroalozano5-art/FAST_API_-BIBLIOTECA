import { createRouter, createWebHistory } from "vue-router";
import CatalogView from "../views/CatalogView.vue";
import BookDetailView from "../views/BookDetailView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "catalog",
      component: CatalogView,
    },
    {
      path: "/libros/:id",
      name: "book-detail",
      component: BookDetailView,
      props: true,
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: { name: "catalog" },
    },
  ],
  scrollBehavior() {
    return { top: 0 };
  },
});

export default router;
