# HU-AT10 — CRUD de categorías de modelos

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Crear, editar y desactivar categorías de modelos  
**Para:** Ajustar la taxonomía

## Criterios de aceptación

- `POST`, `PUT` y `DELETE /api/v1/admin/categories?scope=models` requieren rol `admin`.
- Los cambios generan una nueva `TaxonomyVersion` de modelos.
- `DELETE` es soft delete.
- No se puede borrar una categoría con votos asociados en la versión activa.
- La operación se registra en `AuditLog`.
