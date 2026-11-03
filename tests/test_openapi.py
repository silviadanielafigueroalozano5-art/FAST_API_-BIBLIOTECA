def test_endpoints_documentan_resumen_y_errores_comunes(client):
    schema = client.get("/openapi.json").json()
    for operaciones in schema["paths"].values():
        for metodo, detalle in operaciones.items():
            if metodo not in {"get", "post", "patch", "delete", "put"}:
                continue
            assert detalle["summary"]
            assert {"401", "403", "404"} <= set(detalle["responses"])
