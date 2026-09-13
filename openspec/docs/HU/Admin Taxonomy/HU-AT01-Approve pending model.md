# HU-AT01 — Aprobar modelo pendiente

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Aprobar modelos ingresados por ingesta  
**Para:** Que aparezcan en el catálogo público

## Criterios de aceptación

- `POST /api/v1/admin/models/{id}/approve` requiere rol `admin`.
- Valida `provider_id`, `slug`, `display_name`, `modality` y al menos un `ModelHosting`.
- Cambia `status` a `approved`.
- Registra en `AuditLog` quién aprobó y cuándo.
- Si el modelo ya está `approved`, devuelve `204 No Content` de forma idempotente.
