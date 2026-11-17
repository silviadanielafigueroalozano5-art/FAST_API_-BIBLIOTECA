<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  src: { type: String, default: null },
  alt: { type: String, default: "Portada del libro" },
  size: { type: String, default: "card" },
});

const failed = ref(false);

watch(
  () => props.src,
  () => {
    failed.value = false;
  },
);
</script>

<template>
  <div class="book-cover" :class="`book-cover--${size}`">
    <img v-if="src && !failed" :src="src" :alt="alt" loading="lazy" @error="failed = true" />
    <div v-else class="cover-placeholder" aria-label="Libro sin portada">
      <svg viewBox="0 0 64 72" aria-hidden="true">
        <path d="M12 8.5A5.5 5.5 0 0 1 17.5 3H53v58H17.5a5.5 5.5 0 0 0-5.5 5.5z" />
        <path d="M12 8.5v58A5.5 5.5 0 0 1 17.5 61H53" />
        <path d="M23 18h20M23 26h20M23 34h14" />
      </svg>
      <span>Sin portada</span>
    </div>
  </div>
</template>
