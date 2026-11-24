export function getErrorMessage(error, fallback) {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).filter(Boolean).join(". ");
  }
  if (error.code === "ERR_NETWORK") {
    return "No fue posible conectar con la API. Revisa que FastAPI esté encendido y CORS permita este origen.";
  }
  if (error.code === "ECONNABORTED") {
    return "La API tardó demasiado en responder. Inténtalo de nuevo.";
  }
  return fallback;
}
