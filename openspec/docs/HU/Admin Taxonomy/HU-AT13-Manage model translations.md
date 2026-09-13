# HU-AT13 — Gestionar traducciones de categorías y modelos

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Editar traducciones de categorías de modelos y modelos  
**Para:** Mantener una internacionalización correcta

## Criterios de aceptación

- `PUT /api/v1/admin/categories/{id}/translations/{locale}` gestiona traducciones de categorías.
- `PUT /api/v1/admin/models/{id}/translations/{locale}` gestiona traducciones de modelos.
- Los locales permitidos son `en`, `es`, `pt`, `fr` y `zh`.
- No se puede borrar la traducción `en`, que sirve de fallback.
- Las operaciones se registran en `AuditLog`.
