<script setup>
import { computed, inject, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import BookCover from "../components/BookCover.vue";
import BookFormModal from "../components/BookFormModal.vue";
import { currentUser, isAdmin, isAuthenticated, isStaff } from "../services/auth";
import { getErrorMessage } from "../services/errors";
import {
  createLoan,
  deleteBook,
  getBook,
  listAuthors,
  listCategories,
  listMembers,
  requestMyLoan,
  replaceBookCover,
  updateBook,
} from "../services/library";

const route = useRoute();
const router = useRouter();
const openLogin = inject("openLogin");
const book = ref(null);
const loading = ref(true);
const errorMessage = ref("");
const modalOpen = ref(false);
const authors = ref([]);
const categories = ref([]);
const taxonomyError = ref("");
const formError = ref("");
const saving = ref(false);
const deleting = ref(false);
const notice = ref("");
const loanOpen = ref(false);
const members = ref([]);
const selectedMemberId = ref("");
const loanDate = ref("");
const loanDays = ref(14);
const loanSaving = ref(false);
const loanError = ref("");
let requestSequence = 0;

const bookId = computed(() => Number(route.params.id));
const availabilityClass = computed(() =>
  book.value?.disponibles > 0 ? "availability--available" : "availability--unavailable",
);

async function loadBook() {
  const sequence = ++requestSequence;
  loading.value = true;
  errorMessage.value = "";
  notice.value = "";
  try {
    const result = await getBook(bookId.value);
    if (sequence === requestSequence) {
      book.value = result;
    }
  } catch (error) {
    if (sequence === requestSequence) {
      errorMessage.value = getErrorMessage(error, "No se pudo consultar este libro.");
    }
  } finally {
    if (sequence === requestSequence) {
      loading.value = false;
    }
  }
}

async function openEditForm() {
  if (!isStaff.value) {
    openLogin?.();
    return;
  }
  taxonomyError.value = "";
  formError.value = "";
  try {
    const [authorPage, categoryPage] = await Promise.all([listAuthors(), listCategories()]);
    authors.value = authorPage.items;
    categories.value = categoryPage.items;
    modalOpen.value = true;
  } catch (error) {
    taxonomyError.value = getErrorMessage(error, "No se cargaron autores y categorías.");
  }
}

async function saveChanges({ fields, image }) {
  saving.value = true;
  formError.value = "";
  let detailsSaved = false;
  try {
    await updateBook(bookId.value, fields);
    detailsSaved = true;
    if (image) {
      await replaceBookCover(bookId.value, image);
    }
    modalOpen.value = false;
    await loadBook();
    notice.value = "Los cambios se guardaron correctamente.";
  } catch (error) {
    formError.value = detailsSaved
      ? `Los datos del libro se guardaron, pero la portada no se pudo actualizar. ${getErrorMessage(error, "Inténtalo de nuevo.")}`
      : getErrorMessage(error, "No se pudieron guardar los cambios.");
    if (detailsSaved) {
      await loadBook();
    }
  } finally {
    saving.value = false;
  }
}

async function removeBook() {
  if (!book.value || !isAdmin.value) {
    return;
  }

  const accepted = window.confirm(`¿Eliminar “${book.value.titulo}” del catálogo?`);
  if (!accepted) {
    return;
  }

  deleting.value = true;
  errorMessage.value = "";
  try {
    await deleteBook(bookId.value);
    await router.replace({ name: "catalog" });
  } catch (error) {
    errorMessage.value = getErrorMessage(error, "No se pudo eliminar el libro.");
  } finally {
    deleting.value = false;
  }
}

async function openLoanForm() {
  loanError.value = "";
  if (!isAuthenticated.value) {
    openLogin?.();
    return;
  }
  if (!isStaff.value) {
    await requestLoanForCurrentMember();
    return;
  }
  try {
    members.value = (await listMembers({ activo: true })).items;
    selectedMemberId.value = "";
    loanDate.value = "";
    loanDays.value = 14;
    loanOpen.value = true;
  } catch (error) {
    loanError.value = getErrorMessage(error, "No se pudieron cargar los socios.");
  }
}

async function requestLoanForCurrentMember() {
  if (!currentUser.value?.socio_id) {
    loanError.value = "Tu cuenta no tiene un perfil de socio asociado.";
    return;
  }
  loanSaving.value = true;
  try {
    await requestMyLoan(bookId.value);
    await loadBook();
    notice.value = "Préstamo solicitado y registrado correctamente.";
  } catch (error) {
    loanError.value = getErrorMessage(error, "No se pudo solicitar el préstamo.");
  } finally {
    loanSaving.value = false;
  }
}

async function saveLoan() {
  if (!selectedMemberId.value) {
    loanError.value = "Selecciona un socio.";
    return;
  }
  loanSaving.value = true;
  loanError.value = "";
  try {
    await createLoan({
      libro_id: bookId.value,
      socio_id: Number(selectedMemberId.value),
      fecha_prestamo: loanDate.value || null,
      dias: Number(loanDays.value),
    });
    loanOpen.value = false;
    await loadBook();
    notice.value = "Préstamo registrado correctamente.";
  } catch (error) {
    loanError.value = getErrorMessage(error, "No se pudo registrar el préstamo.");
  } finally {
    loanSaving.value = false;
  }
}

watch(() => route.params.id, loadBook, { immediate: true });
</script>

<template>
  <section class="detail-page">
    <RouterLink class="back-link" :to="{ name: 'catalog' }">
      <span aria-hidden="true">←</span> Volver al catálogo
    </RouterLink>

    <div v-if="loading" class="detail-loading" aria-busy="true">
      <div class="detail-loading__cover"></div>
      <div class="detail-loading__text">
        <div></div><div></div><div></div>
      </div>
    </div>

    <div v-else-if="errorMessage" class="empty-state empty-state--error">
      <span class="empty-state__symbol" aria-hidden="true">!</span>
      <h2>No pudimos abrir este libro</h2>
      <p>{{ errorMessage }}</p>
      <button class="button button--outline" type="button" @click="loadBook">Reintentar</button>
    </div>

    <article v-else-if="book" class="book-detail">
      <div class="book-detail__cover-wrap">
        <BookCover :src="book.imagen_url" :alt="`Portada de ${book.titulo}`" size="detail" />
        <span class="cover-caption">PORTADA DE LA COLECCIÓN</span>
      </div>

      <div class="book-detail__content">
        <span class="eyebrow">FICHA DEL LIBRO · N.º {{ book.id }}</span>
        <h1>{{ book.titulo }}</h1>
        <p class="book-detail__author">
          {{ book.autor.nombre }}
          <span v-if="book.autor.nacionalidad"> · {{ book.autor.nacionalidad }}</span>
        </p>

        <div class="book-detail__badges">
          <span class="availability" :class="availabilityClass">
            <i aria-hidden="true"></i>
            {{ book.disponibles > 0 ? `${book.disponibles} disponibles` : "Sin ejemplares disponibles" }}
          </span>
          <span class="detail-badge">{{ book.anio_publicacion }}</span>
        </div>

        <p v-if="notice" class="inline-success" role="status">{{ notice }}</p>
        <p v-if="taxonomyError" class="inline-alert" role="alert">{{ taxonomyError }}</p>

        <div class="detail-divider"></div>
        <dl class="book-facts">
          <div>
            <dt>ISBN</dt>
            <dd>{{ book.isbn }}</dd>
          </div>
          <div>
            <dt>Ejemplares</dt>
            <dd>{{ book.ejemplares }}</dd>
          </div>
          <div>
            <dt>En préstamo</dt>
            <dd>{{ book.prestamos_activos }}</dd>
          </div>
          <div v-if="book.autor.anio_nacimiento">
            <dt>Nacimiento del autor</dt>
            <dd>{{ book.autor.anio_nacimiento }}</dd>
          </div>
        </dl>

        <div v-if="book.categorias?.length" class="detail-categories">
          <span class="detail-categories__label">Categorías</span>
          <div class="tag-list">
            <span v-for="category in book.categorias" :key="category.id" class="category-tag">
              {{ category.nombre }}
            </span>
          </div>
        </div>

        <div v-if="isStaff || book.disponibles > 0" class="book-detail__actions">
          <button
            v-if="book.disponibles > 0"
            class="button button--primary"
            type="button"
            :disabled="loanSaving"
            @click="openLoanForm"
          >
            {{ loanSaving
              ? "Solicitando…"
              : isStaff
                ? "Registrar préstamo"
                : isAuthenticated
                  ? "Solicitar préstamo"
                  : "Inicia sesión para pedirlo" }}
          </button>
          <template v-if="isStaff">
            <button class="button button--primary" type="button" @click="openEditForm">
              Editar ficha
            </button>
            <button
              v-if="isAdmin"
              class="button button--danger-quiet"
              type="button"
              :disabled="deleting"
              @click="removeBook"
            >
              {{ deleting ? "Eliminando…" : "Eliminar libro" }}
            </button>
          </template>
        </div>
        <p v-if="loanError && !loanOpen" class="form-error form-error--block" role="alert">
          {{ loanError }}
        </p>
        <p v-if="errorMessage" class="form-error form-error--block" role="alert">{{ errorMessage }}</p>
      </div>
    </article>

    <BookFormModal
      v-if="modalOpen && book"
      :book="book"
      :authors="authors"
      :categories="categories"
      :busy="saving"
      :error="formError"
      @close="modalOpen = false"
      @submit="saveChanges"
    />
    <div v-if="loanOpen" class="modal-backdrop" @click.self="loanOpen = false">
      <section class="dialog" role="dialog" aria-modal="true" aria-labelledby="loan-title">
        <button class="dialog__close" type="button" aria-label="Cerrar" @click="loanOpen = false">×</button>
        <span class="eyebrow">NUEVO PRÉSTAMO</span>
        <h2 id="loan-title">{{ book.titulo }}</h2>
        <form class="stack-form" @submit.prevent="saveLoan">
          <label>
            Socio
            <select v-model="selectedMemberId" required>
              <option value="">Selecciona un socio</option>
              <option v-for="member in members" :key="member.id" :value="String(member.id)">
                {{ member.nombre }} · {{ member.email }}
              </option>
            </select>
          </label>
          <label>
            Fecha del préstamo <span class="field-optional">(opcional)</span>
            <input v-model="loanDate" type="date" />
          </label>
          <label>
            Días de préstamo
            <input v-model.number="loanDays" type="number" min="1" max="30" required />
          </label>
          <p v-if="loanError" class="form-error" role="alert">{{ loanError }}</p>
          <div class="dialog__actions">
            <button class="button button--outline" type="button" @click="loanOpen = false">Cancelar</button>
            <button class="button button--primary" type="submit" :disabled="loanSaving">
              {{ loanSaving ? "Registrando…" : "Registrar préstamo" }}
            </button>
          </div>
        </form>
      </section>
    </div>
  </section>
</template>
