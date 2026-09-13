# HU-AT08 — CRUD de proveedores

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Crear, editar y desactivar proveedores  
**Para:** Mantener el catálogo al día

## Criterios de aceptación

- `POST`, `PUT` y `DELETE /api/v1/admin/providers` requieren rol `admin`.
- `DELETE` es soft delete y cambia `status` a `deprecated`.
- No se puede borrar un proveedor con modelos activos.
- El `slug` debe ser único.
- La operación se registra en `AuditLog`.
