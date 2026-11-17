<script setup>
import { ref } from "vue";
import { getErrorMessage } from "../services/errors";
import { signIn } from "../services/auth";

const emit = defineEmits(["close", "success"]);
const email = ref("");
const password = ref("");
const loading = ref(false);
const errorMessage = ref("");

async function submitLogin() {
  loading.value = true;
  errorMessage.value = "";
  try {
    await signIn(email.value.trim(), password.value);
    emit("success");
  } catch (error) {
    errorMessage.value = getErrorMessage(error, "No se pudo iniciar sesión.");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <section class="dialog login-dialog" role="dialog" aria-modal="true" aria-labelledby="login-title">
      <button class="dialog__close" type="button" aria-label="Cerrar" @click="emit('close')">×</button>
      <span class="eyebrow">ACCESO DE PERSONAL</span>
      <h2 id="login-title">Qué bueno verte</h2>
      <p class="dialog__intro">Inicia sesión para gestionar el catálogo de la biblioteca.</p>
      <form class="stack-form" @submit.prevent="submitLogin">
        <label>
          Correo electrónico
          <input v-model="email" type="email" autocomplete="username" required autofocus />
        </label>
        <label>
          Contraseña
          <input v-model="password" type="password" autocomplete="current-password" required />
        </label>
        <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
        <button class="button button--primary button--wide" type="submit" :disabled="loading">
          {{ loading ? "Ingresando…" : "Iniciar sesión" }}
        </button>
      </form>
    </section>
  </div>
</template>
