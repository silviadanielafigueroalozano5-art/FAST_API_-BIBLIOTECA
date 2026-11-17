<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import BookCard from "../components/BookCard.vue";
import BookFormModal from "../components/BookFormModal.vue";
import {
  createBook,
  getLibrarySummary,
  listAuthors,
  listBooks,
  listCategories,
} from "../services/library";
import { getErrorMessage } from "../services/errors";
import { isAuthenticated, isStaff } from "../services/auth";

const router = useRouter();
const openLogin = inject("openLogin");
const books = ref([]);
const categories = ref([]);
const authors = ref([]);
const summary = ref(null);
const total = ref(0);
const skip = ref(0);
const limit = 9;
const searchText = ref("");
const searchField = ref("titulo");
const categoryFilter = ref("");
const order = ref("-anio");
const loading = ref(false);
const taxonomyLoading = ref(false);
const saving = ref(false);
const createOpen = ref(false);
const errorMessage = ref("");
const summaryError = ref("");
const taxonomyError = ref("");
const formError = ref("");
let searchTimer;
let requestSequence = 0;

const pageNumber = computed(() => Math.floor(skip.value / limit) + 1);
const pageCount = computed(() => Math.ceil(total.value / limit));
const rangeStart = computed(() => (total.value ? skip.value + 1 : 0));
const rangeEnd = computed(() => Math.min(skip.value + books.value.length, total.value));

function formatNumber(value) {
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 }).format(Number(value || 0));
}

async function loadBooks() {
  const sequence = ++requestSequence;
  loading.value = true;
  errorMessage.value = "";
  const params = { skip: skip.value, limit };
  if (searchText.value.trim()) {
    params[searchField.value === "autor" ? "autor" : "buscar"] = searchText.value.trim();
  }
  if (categoryFilter.value) {
    params.categoria_id = Number(categoryFilter.value);
  }
  if (order.value) {
    params.orden = order.value;
  }

  try {
    const result = await listBooks(params);
    if (sequence !== requestSequence) {
      return;
    }
    books.value = result.items;
    total.value = result.total;
  } catch (error) {
    if (sequence === requestSequence) {
      errorMessage.value = getErrorMessage(error, "No se pudo cargar el catálogo.");
    }
  } finally {
    if (sequence === requestSequence) {
      loading.value = false;
    }
  }
}

async function loadCategories() {
  try {
    categories.value = (await listCategories()).items;
  } catch (error) {
    taxonomyError.value = getErrorMessage(error, "No se pudieron cargar las categorías.");
  }
}

async function loadSummary() {
  if (!isStaff.value) {
    summary.value = null;
    summaryError.value = "";
    return;
  }
  summaryError.value = "";
  try {
    summary.value = await getLibrarySummary();
  } catch (error) {
    summaryError.value = getErrorMessage(error, "No se pudieron cargar las estadísticas.");
  }
}

function applyFilters() {
  skip.value = 0;
  loadBooks();
}

function onSearchInput() {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(applyFilters, 350);
}

function changePage(nextSkip) {
  skip.value = nextSkip;
  loadBooks();
}

function clearFilters() {
  searchText.value = "";
  categoryFilter.value = "";
  skip.value = 0;
  loadBooks();
}

async function openCreateForm() {
  if (!isStaff.value) {
    if (isAuthenticated.value) {
      taxonomyError.value = "Solo bibliotecarios y administradores pueden registrar libros.";
    } else {
      openLogin?.();
    }
    return;
  }
  formError.value = "";
  taxonomyError.value = "";
  taxonomyLoading.value = true;
  try {
    const [authorPage, categoryPage] = await Promise.all([listAuthors(), listCategories()]);
    authors.value = authorPage.items;
    categories.value = categoryPage.items;
    createOpen.value = true;
  } catch (error) {
    taxonomyError.value = getErrorMessage(error, "No se cargaron autores y categorías.");
  } finally {
    taxonomyLoading.value = false;
  }
}

async function saveNewBook(payload) {
  saving.value = true;
  formError.value = "";
  try {
    const book = await createBook(payload);
    createOpen.value = false;
    skip.value = 0;
    await loadBooks();
    await router.push({ name: "book-detail", params: { id: book.id } });
  } catch (error) {
    formError.value = getErrorMessage(error, "No se pudo registrar el libro.");
  } finally {
    saving.value = false;
  }
}

watch(searchField, applyFilters);
watch(categoryFilter, applyFilters);
watch(order, applyFilters);
watch(isStaff, loadSummary, { immediate: true });

onMounted(() => {
  loadBooks();
  loadCategories();
});

onBeforeUnmount(() => window.clearTimeout(searchTimer));
</script>

<template>
  <section class="catalog-page">
    <div class="page-heading">
      <div>
        <span class="eyebrow">LECTURAS QUE NOS ENCUENTRAN</span>
        <h1>Un lugar para cada historia</h1>
        <p class="page-heading__description">
          Explora el catálogo, descubre nuevos autores y encuentra tu próxima lectura.
        </p>
      </div>
      <button
        class="button button--primary"
        type="button"
        :disabled="taxonomyLoading"
        @click="openCreateForm"
      >
        <span aria-hidden="true">＋</span>
        {{ taxonomyLoading ? "Preparando…" : "Agregar libro" }}
      </button>
    </div>

    <p v-if="taxonomyError" class="inline-alert" role="alert">{{ taxonomyError }}</p>

    <section v-if="isStaff && summary" class="stats-grid" aria-label="Resumen de la biblioteca">
      <article class="stat-card">
        <span class="stat-card__label">Títulos en catálogo</span>
        <strong>{{ formatNumber(summary.total_libros) }}</strong>
        <span class="stat-card__detail">Libros registrados</span>
      </article>
      <article class="stat-card stat-card--accent">
        <span class="stat-card__label">Ejemplares</span>
        <strong>{{ formatNumber(summary.total_ejemplares) }}</strong>
        <span class="stat-card__detail">Copias disponibles en colección</span>
      </article>
      <article class="stat-card">
        <span class="stat-card__label">En préstamo</span>
        <strong>{{ formatNumber(summary.total_prestados) }}</strong>
        <span class="stat-card__detail">Préstamos activos</span>
      </article>
      <article class="stat-card">
        <span class="stat-card__label">Socios activos</span>
        <strong>{{ formatNumber(summary.socios_activos) }}</strong>
        <span class="stat-card__detail">Comunidad lectora</span>
      </article>
    </section>
    <p v-else-if="isStaff && summaryError" class="inline-alert" role="alert">{{ summaryError }}</p>

    <section class="catalog-section" aria-labelledby="catalog-title">
      <div class="section-heading">
        <div>
          <span class="eyebrow">LA COLECCIÓN</span>
          <h2 id="catalog-title">Catálogo de libros</h2>
        </div>
        <span class="result-count">{{ formatNumber(total) }} títulos</span>
      </div>

      <div class="catalog-toolbar">
        <label class="search-control">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="10.8" cy="10.8" r="6.8" />
            <path d="m16 16 4.5 4.5" />
          </svg>
          <span class="sr-only">Buscar en el catálogo</span>
          <input
            v-model="searchText"
            type="search"
            :placeholder="searchField === 'autor' ? 'Buscar por autor…' : 'Buscar por título…'"
            @input="onSearchInput"
          />
          <select v-model="searchField" aria-label="Campo de búsqueda">
            <option value="titulo">Título</option>
            <option value="autor">Autor</option>
          </select>
        </label>

        <label class="filter-control">
          <span class="sr-only">Filtrar por categoría</span>
          <select v-model="categoryFilter">
            <option value="">Todas las categorías</option>
            <option v-for="category in categories" :key="category.id" :value="String(category.id)">
              {{ category.nombre }}
            </option>
          </select>
        </label>

        <label class="filter-control">
          <span class="sr-only">Ordenar libros</span>
          <select v-model="order">
            <option value="-anio">Más recientes</option>
            <option value="anio">Más antiguos</option>
            <option value="titulo">Título A–Z</option>
            <option value="-titulo">Título Z–A</option>
          </select>
        </label>
      </div>

      <div v-if="loading" class="book-grid" aria-label="Cargando libros" aria-busy="true">
        <div v-for="item in 6" :key="item" class="book-skeleton">
          <div class="book-skeleton__cover"></div>
          <div class="book-skeleton__line"></div>
          <div class="book-skeleton__line book-skeleton__line--short"></div>
        </div>
      </div>

      <div v-else-if="errorMessage" class="empty-state empty-state--error">
        <span class="empty-state__symbol" aria-hidden="true">!</span>
        <h3>No pudimos abrir el catálogo</h3>
        <p>{{ errorMessage }}</p>
        <button class="button button--outline" type="button" @click="loadBooks">Reintentar</button>
      </div>

      <div v-else-if="!books.length" class="empty-state">
        <span class="empty-state__symbol" aria-hidden="true">⌕</span>
        <h3>{{ searchText || categoryFilter ? "No encontramos coincidencias" : "Aún no hay libros" }}</h3>
        <p>
          {{ searchText || categoryFilter
            ? "Prueba con otro término o cambia los filtros."
            : "Cuando se registren libros, aparecerán aquí." }}
        </p>
        <button v-if="searchText || categoryFilter" class="button button--quiet" type="button" @click="clearFilters">
          Limpiar búsqueda
        </button>
      </div>

      <div v-else class="book-grid">
        <BookCard v-for="book in books" :key="book.id" :book="book" />
      </div>

      <nav v-if="!loading && !errorMessage && total > limit" class="pagination" aria-label="Paginación del catálogo">
        <span>{{ rangeStart }}–{{ rangeEnd }} de {{ total }}</span>
        <div class="pagination__controls">
          <button
            class="button button--quiet button--small"
            type="button"
            :disabled="skip === 0"
            aria-label="Página anterior"
            @click="changePage(Math.max(0, skip - limit))"
          >
            ← Anterior
          </button>
          <span>Página {{ pageNumber }} de {{ pageCount }}</span>
          <button
            class="button button--quiet button--small"
            type="button"
            :disabled="skip + limit >= total"
            aria-label="Página siguiente"
            @click="changePage(skip + limit)"
          >
            Siguiente →
          </button>
        </div>
      </nav>
    </section>

    <BookFormModal
      v-if="createOpen"
      :authors="authors"
      :categories="categories"
      :busy="saving"
      :error="formError"
      @close="createOpen = false"
      @submit="saveNewBook"
    />
  </section>
</template>
