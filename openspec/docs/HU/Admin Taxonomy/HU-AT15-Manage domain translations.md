# HU-AT15 — Gestionar traducciones de dominios

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Editar traducciones de dominios y subdominios  
**Para:** Mantener una internacionalización correcta en la clasificación de problemas

## Criterios de aceptación

- `PUT /api/v1/admin/domains/{id}/translations/{locale}` gestiona traducciones de dominios.
- Los locales permitidos son `en`, `es`, `pt`, `fr` y `zh`.
- No se puede borrar la traducción `en`.
- Las operaciones se registran en `AuditLog`.
