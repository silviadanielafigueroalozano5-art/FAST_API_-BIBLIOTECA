<script setup>
import { onMounted, onUnmounted, provide, ref } from "vue";
import { RouterView } from "vue-router";
import SidebarNav from "./components/SidebarNav.vue";
import LoginModal from "./components/LoginModal.vue";
import { clearSession, currentUser, signOut } from "./services/auth";

const loginOpen = ref(false);
const sessionNotice = ref("");

provide("openLogin", () => {
  sessionNotice.value = "";
  loginOpen.value = true;
});

function handleExpiredSession() {
  clearSession();
  sessionNotice.value = "Tu sesión terminó. Vuelve a iniciar sesión para continuar.";
}

function handleLoginSuccess() {
  loginOpen.value = false;
  sessionNotice.value = "";
}

async function logout() {
  try {
    await signOut();
    sessionNotice.value = "Sesión cerrada.";
  } catch {
    sessionNotice.value = "Se cerró la sesión en este navegador; no se pudo confirmar su revocación en la API.";
  }
}

onMounted(() => window.addEventListener("biblioteca:auth-expired", handleExpiredSession));
onUnmounted(() => window.removeEventListener("biblioteca:auth-expired", handleExpiredSession));
</script>

<template>
  <div class="app-shell">
    <SidebarNav />
    <div class="workspace">
      <header class="topbar">
        <div class="topbar__context">
          <span class="eyebrow">BIBLIOTECA DIGITAL</span>
          <span>Gestión del catálogo</span>
        </div>
        <div class="topbar__account">
          <template v-if="currentUser">
            <div class="account-chip">
              <span class="account-chip__avatar">{{ currentUser.nombre?.slice(0, 1) || "B" }}</span>
              <span class="account-chip__details">
                <strong>{{ currentUser.nombre }}</strong>
                <small>{{ currentUser.rol }}</small>
              </span>
            </div>
            <button class="button button--quiet button--small" type="button" @click="logout">
              Salir
            </button>
          </template>
          <button v-else class="button button--outline button--small" type="button" @click="loginOpen = true">
            Iniciar sesión
          </button>
        </div>
      </header>

      <main class="main-content">
        <p v-if="sessionNotice" class="session-notice" role="status">{{ sessionNotice }}</p>
        <RouterView />
      </main>
      <footer class="app-footer">
        <span>Biblioteca</span>
        <span>Un espacio para descubrir nuevas historias</span>
      </footer>
    </div>

    <LoginModal
      v-if="loginOpen"
      @close="loginOpen = false"
      @success="handleLoginSuccess"
    />
  </div>
</template>
