<script setup>
import { onBeforeUnmount, reactive, ref, watch } from "vue";
import BookCover from "./BookCover.vue";
import { createAuthor } from "../services/library";
import { getErrorMessage } from "../services/errors";

const props = defineProps({
  book: { type: Object, default: null },
  authors: { type: Array, default: () => [] },
  categories: { type: Array, default: () => [] },
  busy: { type: Boolean, default: false },
  error: { type: String, default: "" },
});

const emit = defineEmits(["close", "submit"]);
const currentYear = new Date().getFullYear();
const form = reactive({
  titulo: "",
  isbn: "",
  anio_publicacion: currentYear,
  ejemplares: 1,
  autor_id: "",
  categoria_ids: [],
});
const imageFile = ref(null);
const imagePreview = ref("");
const imageError = ref("");
const categoryError = ref("");
const authorOptions = ref([...props.authors]);
const addAuthorOpen = ref(false);
const authorBusy = ref(false);
const authorError = ref("");
const authorNotice = ref("");
const newAuthor = reactive({
  nombre: "",
  nacionalidad: "",
  anio_nacimiento: "",
});

watch(
  () => props.authors,
  (authors) => {
    authorOptions.value = [...authors];
  },
  { immediate: true },
);

watch(
  () => props.book,
  (book) => {
    form.titulo = book?.titulo || "";
    form.isbn = book?.isbn || "";
    form.anio_publicacion = book?.anio_publicacion || currentYear;
    form.ejemplares = book?.ejemplares || 1;
    form.autor_id = book?.autor_id || book?.autor?.id || "";
    form.categoria_ids = book
      ? (book.categorias || []).map((category) => category.id)
      : [];
    imageFile.value = null;
    clearPreview();
    imageError.value = "";
    categoryError.value = "";
    addAuthorOpen.value = false;
    authorError.value = "";
    authorNotice.value = "";
  },
  { immediate: true },
);

function clearPreview() {
  if (imagePreview.value) {
    URL.revokeObjectURL(imagePreview.value);
    imagePreview.value = "";
  }
}

function selectImage(event) {
  const file = event.target.files?.[0];
  imageError.value = "";
  imageFile.value = null;
  clearPreview();
  if (!file) {
    return;
  }
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
    imageError.value = "Selecciona un archivo JPEG, PNG o WebP.";
    event.target.value = "";
    return;
  }
  if (file.size > 2 * 1024 * 1024) {
    imageError.value = "La imagen no puede superar los 2 MB.";
    event.target.value = "";
    return;
  }
  imageFile.value = file;
  imagePreview.value = URL.createObjectURL(file);
}

function limitCategories() {
  categoryError.value = "";
  if (form.categoria_ids.length > 5) {
    form.categoria_ids = form.categoria_ids.slice(0, 5);
    categoryError.value = "Puedes seleccionar como máximo cinco categorías.";
  }
}

function toggleAuthorForm() {
  addAuthorOpen.value = !addAuthorOpen.value;
  authorError.value = "";
  authorNotice.value = "";
}

async function saveAuthor() {
  authorError.value = "";
  authorNotice.value = "";
  if (newAuthor.nombre.trim().length < 2) {
    authorError.value = "El nombre del autor debe tener al menos 2 caracteres.";
    return;
  }

  const birthYear = newAuthor.anio_nacimiento
    ? Number(newAuthor.anio_nacimiento)
    : null;
  if (
    birthYear !== null &&
    (!Number.isInteger(birthYear) || birthYear < 1000 || birthYear > currentYear)
  ) {
    authorError.value = `El año de nacimiento debe estar entre 1000 y ${currentYear}.`;
    return;
  }

  authorBusy.value = true;
  try {
    const author = await createAuthor({
      nombre: newAuthor.nombre.trim(),
      nacionalidad: newAuthor.nacionalidad.trim() || null,
      anio_nacimiento: birthYear,
    });
    authorOptions.value = [...authorOptions.value, author].sort((a, b) =>
      a.nombre.localeCompare(b.nombre, "es"),
    );
    form.autor_id = author.id;
    newAuthor.nombre = "";
    newAuthor.nacionalidad = "";
    newAuthor.anio_nacimiento = "";
    addAuthorOpen.value = false;
    authorNotice.value = `Autor “${author.nombre}” agregado y seleccionado.`;
  } catch (error) {
    authorError.value = getErrorMessage(error, "No se pudo agregar el autor.");
  } finally {
    authorBusy.value = false;
  }
}

function submitForm() {
  if (imageError.value || categoryError.value) {
    return;
  }
  emit("submit", {
    fields: {
      titulo: form.titulo.trim(),
      isbn: form.isbn.trim(),
      anio_publicacion: Number(form.anio_publicacion),
      ejemplares: Number(form.ejemplares),
      autor_id: Number(form.autor_id),
      categoria_ids: [...form.categoria_ids].map(Number),
    },
    image: imageFile.value,
  });
}

onBeforeUnmount(clearPreview);
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <section
      class="dialog book-form-dialog"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="book ? 'edit-book-title' : 'create-book-title'"
    >
      <button class="dialog__close" type="button" aria-label="Cerrar" @click="emit('close')">×</button>
      <span class="eyebrow">{{ book ? "ACTUALIZAR CATÁLOGO" : "NUEVA INCORPORACIÓN" }}</span>
      <h2 :id="book ? 'edit-book-title' : 'create-book-title'">
        {{ book ? "Editar información" : "Agregar un libro" }}
      </h2>
      <p class="dialog__intro">
        {{ book ? "La portada actual se conserva si no seleccionas otra." : "Completa la ficha para incorporar una nueva historia." }}
      </p>

      <form class="book-form" @submit.prevent="submitForm">
        <div class="book-form__fields">
          <label class="field field--full">
            Título
            <input v-model="form.titulo" maxlength="150" required placeholder="El nombre del libro" />
          </label>
          <label class="field">
            ISBN
            <input
              v-model="form.isbn"
              inputmode="numeric"
              minlength="13"
              maxlength="13"
              pattern="[0-9]{13}"
              required
              placeholder="13 dígitos"
            />
          </label>
          <label class="field">
            Año de publicación
            <input v-model.number="form.anio_publicacion" type="number" min="1450" :max="currentYear" required />
          </label>
          <label class="field">
            Ejemplares
            <input v-model.number="form.ejemplares" type="number" min="1" max="50" required />
          </label>
          <div class="field field--full author-field">
            <div class="author-field__heading">
              <span>Autor</span>
              <button
                class="text-button"
                type="button"
                :aria-expanded="addAuthorOpen"
                aria-controls="add-author-panel"
                @click="toggleAuthorForm"
              >
                {{ addAuthorOpen ? "Cancelar" : "¿No aparece? Agregar autor" }}
              </button>
            </div>
            <select v-model.number="form.autor_id" required>
              <option value="" disabled>Selecciona un autor</option>
              <option v-for="author in authorOptions" :key="author.id" :value="author.id">
                {{ author.nombre }}
              </option>
            </select>
            <small v-if="authorNotice" class="inline-success" role="status">{{ authorNotice }}</small>
            <div v-if="addAuthorOpen" id="add-author-panel" class="author-create-panel">
              <div class="author-create-panel__fields">
                <label class="field">
                  Nombre del autor
                  <input
                    v-model="newAuthor.nombre"
                    maxlength="100"
                    minlength="2"
                    placeholder="Nombre y apellido"
                  />
                </label>
                <label class="field">
                  Nacionalidad <span class="field__hint">Opcional</span>
                  <input v-model="newAuthor.nacionalidad" maxlength="60" placeholder="Ej. Colombiana" />
                </label>
                <label class="field">
                  Año de nacimiento <span class="field__hint">Opcional</span>
                  <input
                    v-model="newAuthor.anio_nacimiento"
                    type="number"
                    min="1000"
                    :max="currentYear"
                    placeholder="Año"
                  />
                </label>
              </div>
              <p v-if="authorError" class="form-error" role="alert">{{ authorError }}</p>
              <button
                class="button button--outline button--small"
                type="button"
                :disabled="authorBusy"
                @click="saveAuthor"
              >
                {{ authorBusy ? "Guardando autor…" : "Guardar y seleccionar" }}
              </button>
            </div>
          </div>
          <label class="field field--full">
            Categorías <span class="field__hint">Puedes elegir hasta cinco</span>
            <select v-model="form.categoria_ids" multiple required size="4" @change="limitCategories">
              <option v-for="category in categories" :key="category.id" :value="category.id">
                {{ category.nombre }}
              </option>
            </select>
            <small v-if="categoryError" class="form-error" role="alert">{{ categoryError }}</small>
            <small v-if="!categories.length" class="field__help">
              No hay categorías disponibles. La API requiere al menos una para registrar un libro.
            </small>
          </label>
        </div>

        <div class="image-picker">
          <div class="image-picker__preview">
            <BookCover
              :src="imagePreview || book?.imagen_url"
              :alt="`Portada de ${form.titulo || 'libro'}`"
              size="form"
            />
          </div>
          <div class="image-picker__body">
            <strong>{{ book ? "Portada" : "Portada del libro" }}</strong>
            <p>{{ imageFile ? imageFile.name : "JPEG, PNG o WebP · Máximo 2 MB" }}</p>
            <label class="button button--outline button--small file-button">
              {{ imageFile ? "Cambiar archivo" : book?.imagen_url ? "Reemplazar portada" : "Elegir imagen" }}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                @change="selectImage"
              />
            </label>
            <span v-if="imageError" class="form-error" role="alert">{{ imageError }}</span>
          </div>
        </div>

        <p v-if="error" class="form-error form-error--block" role="alert">{{ error }}</p>
        <div class="dialog__actions">
          <button class="button button--quiet" type="button" :disabled="busy" @click="emit('close')">
            Cancelar
          </button>
          <button class="button button--primary" type="submit" :disabled="busy || !categories.length">
            {{ busy ? "Guardando…" : book ? "Guardar cambios" : "Registrar libro" }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>
