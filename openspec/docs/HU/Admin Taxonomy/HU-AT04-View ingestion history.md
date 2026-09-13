# HU-AT04 — Ver historial de ingestas

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Ver las corridas de ingesta  
**Para:** Auditar qué se importó y qué falló

## Criterios de aceptación

- `GET /api/v1/admin/ingestion/runs?source=&status=` requiere rol `admin`.
- Incluye fuente, fechas, estado, contadores y errores.
- El resultado es paginado.
