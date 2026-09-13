# HU-AT14 — Gestionar traducciones de orquestadores

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Editar traducciones de orquestadores y sus categorías  
**Para:** Mantener una internacionalización correcta en el dominio de orquestadores

## Criterios de aceptación

- `PUT /api/v1/admin/orchestrators/{id}/translations/{locale}` gestiona traducciones de orquestadores.
- `PUT /api/v1/admin/categories/orchestrators/{id}/translations/{locale}` gestiona traducciones de categorías de orquestadores.
- Los locales permitidos son `en`, `es`, `pt`, `fr` y `zh`.
- No se puede borrar la traducción `en`.
- Las operaciones se registran en `AuditLog`.
