<script setup>
import { ref } from "vue";
import { getErrorMessage } from "../services/errors";
import { registerUser, signIn } from "../services/auth";

const emit = defineEmits(["close", "success"]);
const email = ref("");
const password = ref("");
const name = ref("");
const phone = ref("");
const confirmPassword = ref("");
const mode = ref("login");
const showLoginPassword = ref(false);
const showPassword = ref(false);
const showConfirmPassword = ref(false);
const loading = ref(false);
const errorMessage = ref("");
const successMessage = ref("");

async function submitLogin() {
  loading.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  try {
    await signIn(email.value.trim(), password.value);
    emit("success");
  } catch (error) {
    errorMessage.value = getErrorMessage(error, "No se pudo iniciar sesión.");
  } finally {
    loading.value = false;
  }
}

async function submitRegistration() {
  loading.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  try {
    await registerUser({
      email: email.value.trim(),
      nombre: name.value.trim(),
      telefono: phone.value.trim(),
      password: password.value,
      confirmar_password: confirmPassword.value,
    });
    try {
      await signIn(email.value.trim(), password.value);
      emit("success");
    } catch (error) {
      mode.value = "login";
      password.value = "";
      successMessage.value = "Tu cuenta se creó. Inicia sesión para continuar.";
      errorMessage.value = getErrorMessage(error, "No se pudo iniciar sesión.");
    }
  } catch (error) {
    errorMessage.value = getErrorMessage(error, "No se pudo crear la cuenta.");
  } finally {
    loading.value = false;
  }
}

function switchMode(nextMode) {
  mode.value = nextMode;
  errorMessage.value = "";
  successMessage.value = "";
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <section class="dialog login-dialog" role="dialog" aria-modal="true" aria-labelledby="login-title">
      <button class="dialog__close" type="button" aria-label="Cerrar" @click="emit('close')">×</button>
      <span class="eyebrow">CUENTA DE BIBLIOTECA</span>
      <h2 id="login-title">{{ mode === "login" ? "Qué bueno verte" : "Crea tu cuenta" }}</h2>
      <p v-if="mode === 'login'" class="dialog__intro">Inicia sesión para consultar o gestionar la biblioteca.</p>
      <p v-else class="dialog__intro">Regístrate para quedar asociado como socio y solicitar préstamos.</p>
      <p v-if="successMessage" class="inline-success" role="status">{{ successMessage }}</p>
      <form v-if="mode === 'login'" class="stack-form" @submit.prevent="submitLogin">
        <label>
          Correo electrónico
          <input v-model="email" type="email" autocomplete="username" required autofocus />
        </label>
        <label>
          Contraseña
          <span class="password-input">
            <input
              id="login-password"
              v-model="password"
              :type="showLoginPassword ? 'text' : 'password'"
              autocomplete="current-password"
              required
            />
            <button
              class="password-input__toggle"
              type="button"
              :aria-label="showLoginPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              :aria-pressed="showLoginPassword"
              aria-controls="login-password"
              @click="showLoginPassword = !showLoginPassword"
            >
              <svg v-if="!showLoginPassword" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M2.5 12s3.4-6.2 9.5-6.2 9.5 6.2 9.5 6.2-3.4 6.2-9.5 6.2S2.5 12 2.5 12Z" />
                <circle cx="12" cy="12" r="2.7" />
              </svg>
              <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 3l18 18M10.6 5.9A10.7 10.7 0 0 1 12 5.8c6.1 0 9.5 6.2 9.5 6.2a15 15 0 0 1-3.1 3.8M6.2 6.2C3.8 7.8 2.5 12 2.5 12s3.4 6.2 9.5 6.2c1.4 0 2.6-.4 3.7-1" />
                <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
              </svg>
            </button>
          </span>
        </label>
        <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
        <button class="button button--primary button--wide" type="submit" :disabled="loading">
          {{ loading ? "Ingresando…" : "Iniciar sesión" }}
        </button>
        <p class="form-switch">
          ¿Aún no tienes cuenta?
          <button type="button" @click="switchMode('register')">Crear cuenta de socio</button>
        </p>
      </form>
      <form v-else class="stack-form" @submit.prevent="submitRegistration">
        <label>
          Nombre completo
          <input v-model="name" type="text" minlength="3" maxlength="100" autocomplete="name" required />
        </label>
        <label>
          Correo electrónico
          <input v-model="email" type="email" maxlength="150" autocomplete="email" required />
        </label>
        <label>
          Teléfono <span class="field-optional">(opcional)</span>
          <input v-model="phone" type="tel" maxlength="15" autocomplete="tel" />
        </label>
        <label>
          Contraseña
          <span class="password-input">
            <input
              id="register-password"
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              minlength="8"
              maxlength="64"
              autocomplete="new-password"
              required
            />
            <button
              class="password-input__toggle"
              type="button"
              :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              :aria-pressed="showPassword"
              aria-controls="register-password"
              @click="showPassword = !showPassword"
            >
              <svg v-if="!showPassword" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M2.5 12s3.4-6.2 9.5-6.2 9.5 6.2 9.5 6.2-3.4 6.2-9.5 6.2S2.5 12 2.5 12Z" />
                <circle cx="12" cy="12" r="2.7" />
              </svg>
              <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 3l18 18M10.6 5.9A10.7 10.7 0 0 1 12 5.8c6.1 0 9.5 6.2 9.5 6.2a15 15 0 0 1-3.1 3.8M6.2 6.2C3.8 7.8 2.5 12 2.5 12s3.4 6.2 9.5 6.2c1.4 0 2.6-.4 3.7-1" />
                <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
              </svg>
            </button>
          </span>
          <small>Debe incluir mayúscula, minúscula y número.</small>
        </label>
        <label>
          Confirmar contraseña
          <span class="password-input">
            <input
              id="register-confirm-password"
              v-model="confirmPassword"
              :type="showConfirmPassword ? 'text' : 'password'"
              minlength="8"
              maxlength="64"
              autocomplete="new-password"
              required
            />
            <button
              class="password-input__toggle"
              type="button"
              :aria-label="showConfirmPassword ? 'Ocultar confirmación de contraseña' : 'Mostrar confirmación de contraseña'"
              :aria-pressed="showConfirmPassword"
              aria-controls="register-confirm-password"
              @click="showConfirmPassword = !showConfirmPassword"
            >
              <svg v-if="!showConfirmPassword" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M2.5 12s3.4-6.2 9.5-6.2 9.5 6.2 9.5 6.2-3.4 6.2-9.5 6.2S2.5 12 2.5 12Z" />
                <circle cx="12" cy="12" r="2.7" />
              </svg>
              <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 3l18 18M10.6 5.9A10.7 10.7 0 0 1 12 5.8c6.1 0 9.5 6.2 9.5 6.2a15 15 0 0 1-3.1 3.8M6.2 6.2C3.8 7.8 2.5 12 2.5 12s3.4 6.2 9.5 6.2c1.4 0 2.6-.4 3.7-1" />
                <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
              </svg>
            </button>
          </span>
        </label>
        <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
        <button class="button button--primary button--wide" type="submit" :disabled="loading">
          {{ loading ? "Creando cuenta…" : "Crear cuenta de socio" }}
        </button>
        <p class="form-switch">
          ¿Ya tienes cuenta?
          <button type="button" @click="switchMode('login')">Iniciar sesión</button>
        </p>
      </form>
    </section>
  </div>
</template>
