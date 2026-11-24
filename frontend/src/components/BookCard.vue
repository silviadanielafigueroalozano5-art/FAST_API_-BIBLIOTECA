<script setup>
import { RouterLink } from "vue-router";
import BookCover from "./BookCover.vue";

defineProps({
  book: { type: Object, required: true },
});
</script>

<template>
  <RouterLink class="book-card" :to="{ name: 'book-detail', params: { id: book.id } }">
    <BookCover :src="book.imagen_url" :alt="`Portada de ${book.titulo}`" />
    <div class="book-card__body">
      <div class="book-card__meta">
        <span>{{ book.anio_publicacion }}</span>
        <span class="book-card__dot" aria-hidden="true">·</span>
        <span>{{ book.ejemplares }} {{ book.ejemplares === 1 ? "ejemplar" : "ejemplares" }}</span>
      </div>
      <h2>{{ book.titulo }}</h2>
      <p class="book-card__author">{{ book.autor?.nombre || "Autor no disponible" }}</p>
      <div v-if="book.categorias?.length" class="book-card__tags">
        <span v-for="category in book.categorias.slice(0, 2)" :key="category.id">
          {{ category.nombre }}
        </span>
      </div>
      <div class="book-card__footer">
        <span class="book-card__isbn">ISBN {{ book.isbn }}</span>
        <span class="book-card__arrow" aria-hidden="true">↗</span>
      </div>
    </div>
  </RouterLink>
</template>
