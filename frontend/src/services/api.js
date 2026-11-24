import axios from "axios";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveTokens,
} from "./session";

const apiOrigin = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const api = axios.create({
  baseURL: `${apiOrigin}/api/v1`,
  timeout: 20000,
});

let refreshRequest;

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config;
    const isAuthRequest = /\/auth\/(login|refresh|logout)$/.test(
      request?.url || "",
    );

    if (error.response?.status !== 401 || !request || request._retried || isAuthRequest) {
      return Promise.reject(error);
    }

    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearTokens();
      window.dispatchEvent(new Event("biblioteca:auth-expired"));
      return Promise.reject(error);
    }

    request._retried = true;
    try {
      if (!refreshRequest) {
        refreshRequest = axios
          .post(
            `${api.defaults.baseURL}/auth/refresh`,
            { refresh_token: refreshToken },
            { timeout: api.defaults.timeout },
          )
          .then(({ data }) => {
            saveTokens(data);
            return data.access_token;
          })
          .catch((refreshError) => {
            clearTokens();
            window.dispatchEvent(new Event("biblioteca:auth-expired"));
            throw refreshError;
          })
          .finally(() => {
            refreshRequest = undefined;
          });
      }

      const token = await refreshRequest;
      request.headers.Authorization = `Bearer ${token}`;
      return api(request);
    } catch {
      return Promise.reject(error);
    }
  },
);

export default api;
