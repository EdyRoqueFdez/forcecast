# HU-T02 — Listar modelos aprobados

**Épica:** T — Taxonomía  
**Sprint:** 0

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Ver los modelos disponibles  
**Para:** Saber sobre qué modelos puedo votar o consultar

## Criterios de aceptación

- `GET /api/v1/models` devuelve solo modelos con `status=approved`.
- Soporta filtros por `provider_slug`, `modalities`, `category_slug`, búsqueda y `lang`.
- Incluye `locale_used`.
- La respuesta es paginada y se ordena por `release_date` descendente por defecto.
- La respuesta se cachea durante un TTL configurable por endpoint, con valor por defecto de 60 segundos.
- No expone modelos en estado `draft`, `pending_review`, `rejected` o `deprecated`.
