# HU-AT12 — CRUD de dominios y subdominios

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Crear, editar y desactivar dominios de problemas  
**Para:** Ajustar la clasificación de problemas

## Criterios de aceptación

- `POST`, `PUT` y `DELETE /api/v1/admin/domains` requieren rol `admin`.
- Los cambios generan una nueva `TaxonomyVersion` de dominios.
- `DELETE` es soft delete.
- No se puede borrar un dominio con problemas publicados.
- La operación se registra en `AuditLog`.
