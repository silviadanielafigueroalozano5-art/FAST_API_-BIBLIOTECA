const ACCESS_TOKEN_KEY = "biblioteca.access_token";
const REFRESH_TOKEN_KEY = "biblioteca.refresh_token";

export function getAccessToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

export function saveTokens({ access_token, refresh_token }) {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, access_token);
  sessionStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}
