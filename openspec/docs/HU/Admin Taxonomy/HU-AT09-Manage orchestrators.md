# HU-AT09 — CRUD de orquestadores

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Crear, editar y desactivar orquestadores  
**Para:** Mantener el catálogo de orquestadores al día

## Criterios de aceptación

- `POST`, `PUT` y `DELETE /api/v1/admin/orchestrators` requieren rol `admin`.
- Un orquestador tiene `maintainer` y puede asociarse con uno o varios proveedores.
- `DELETE` es soft delete y cambia `status` a `deprecated`.
- No se puede borrar un orquestador con votos activos.
- El `slug` debe ser único.
- La operación se registra en `AuditLog`.
