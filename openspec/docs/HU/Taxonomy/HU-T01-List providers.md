# HU-T01 — Listar proveedores

**Épica:** T — Taxonomía  
**Sprint:** 0

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Ver la lista de proveedores de IA  
**Para:** Conocer qué empresas están representadas en Forcecast

## Criterios de aceptación

- `GET /api/v1/providers` devuelve solo proveedores con `status=active`.
- Cada item incluye `slug`, nombre, `website`, `logo_url` y `api_docs_url`.
- La respuesta es paginada, con 20 items por defecto y un máximo de 100.
- La respuesta cumple p95 menor de 200 ms.
- Los nombres propios de proveedores no se traducen; las descripciones sí.
