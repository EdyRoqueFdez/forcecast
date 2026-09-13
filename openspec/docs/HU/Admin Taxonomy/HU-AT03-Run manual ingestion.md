# HU-AT03 — Disparar ingesta manual

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Ejecutar ingesta desde una fuente  
**Para:** Actualizar el catálogo bajo demanda

## Criterios de aceptación

- `POST /api/v1/admin/ingestion/run` acepta `{source}` y requiere rol `admin`.
- Las fuentes soportadas son `openrouter`, `huggingface` y `lmsys`.
- Crea `IngestionRun` con estado `running`.
- Al terminar, actualiza contadores y estado.
- La ejecución es idempotente y no duplica modelos.
- Los errores por modelo no abortan el run; se permite éxito parcial.
- Registra `source_payload_hash` para deduplicación.
- El rate limit es de 5 ingestas por hora.
