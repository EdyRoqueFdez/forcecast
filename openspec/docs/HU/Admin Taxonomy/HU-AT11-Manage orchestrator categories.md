# HU-AT11 — CRUD de categorías de orquestadores

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Crear, editar y desactivar categorías de orquestadores  
**Para:** Ajustar su taxonomía

## Criterios de aceptación

- `POST`, `PUT` y `DELETE /api/v1/admin/categories?scope=orchestrators` requieren rol `admin`.
- Se aplican las mismas reglas de soft delete, versionado y auditoría que en HU-AT10, pero sobre la taxonomía de orquestadores.
