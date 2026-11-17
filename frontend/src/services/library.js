import api from "./api";

export async function listBooks(params) {
  return (await api.get("/libros", { params })).data;
}

export async function getBook(id) {
  return (await api.get(`/libros/${id}`)).data;
}

export async function createBook({ fields, image }) {
  const form = new FormData();
  form.append("titulo", fields.titulo);
  form.append("isbn", fields.isbn);
  form.append("anio_publicacion", String(fields.anio_publicacion));
  form.append("ejemplares", String(fields.ejemplares));
  form.append("autor_id", String(fields.autor_id));
  fields.categoria_ids.forEach((id) => form.append("categoria_ids", String(id)));
  if (image) {
    form.append("imagen", image);
  }
  return (await api.post("/libros/con-imagen", form)).data;
}

export async function updateBook(id, fields) {
  return (await api.patch(`/libros/${id}`, fields)).data;
}

export async function replaceBookCover(id, image) {
  const form = new FormData();
  form.append("imagen", image);
  return (await api.post(`/libros/${id}/imagen`, form)).data;
}

export async function deleteBook(id) {
  await api.delete(`/libros/${id}`);
}

export async function listAuthors() {
  return (await api.get("/autores", { params: { skip: 0, limit: 100 } })).data;
}

export async function createAuthor(fields) {
  return (await api.post("/autores", fields)).data;
}

export async function listCategories() {
  return (await api.get("/categorias", { params: { skip: 0, limit: 100 } })).data;
}

export async function getLibrarySummary() {
  return (await api.get("/reportes/resumen")).data;
}
