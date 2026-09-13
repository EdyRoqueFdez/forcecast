# HU-AT02 — Rechazar modelo pendiente

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Rechazar modelos inválidos o duplicados  
**Para:** Mantener el catálogo limpio

## Criterios de aceptación

- `POST /api/v1/admin/models/{id}/reject` acepta `{reason}` y requiere rol `admin`.
- Cambia `status` a `rejected`.
- Guarda la razón en `AuditLog`.
- El modelo rechazado no aparece en la API pública.
