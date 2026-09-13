# HU-AT05 — Gestionar versiones de taxonomía de modelos

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Crear y activar versiones de la taxonomía de modelos  
**Para:** Evolucionar las categorías sin romper el histórico

## Criterios de aceptación

- `POST /api/v1/admin/taxonomy/models/versions` crea una versión de modelos.
- `POST /api/v1/admin/taxonomy/models/versions/{id}/activate` la marca `is_current`.
- Solo una versión puede ser `is_current` a la vez.
- Las versiones previas son inmutables.
- Los cambios en categorías generan automáticamente una nueva versión.
- Los cambios se registran en `AuditLog`.
