import { computed, ref } from "vue";
import api from "./api";
import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from "./session";

export const currentUser = ref(null);
export const isAuthenticated = computed(() => Boolean(currentUser.value));
export const isStaff = computed(() =>
  ["admin", "bibliotecario"].includes(currentUser.value?.rol),
);
export const isAdmin = computed(() => currentUser.value?.rol === "admin");

export function clearSession() {
  clearTokens();
  currentUser.value = null;
}

export async function initializeAuth() {
  if (!getAccessToken()) {
    currentUser.value = null;
    return;
  }

  try {
    currentUser.value = (await api.get("/auth/me")).data;
  } catch {
    clearSession();
  }
}

export async function signIn(email, password) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const { data } = await api.post("/auth/login", form);
  saveTokens(data);
  currentUser.value = (await api.get("/auth/me")).data;
  return currentUser.value;
}

export async function signOut() {
  const refreshToken = getRefreshToken();
  try {
    if (refreshToken) {
      await api.post("/auth/logout", { refresh_token: refreshToken });
    }
  } finally {
    clearSession();
  }
}
