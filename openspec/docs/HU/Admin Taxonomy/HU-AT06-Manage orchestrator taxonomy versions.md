# HU-AT06 — Gestionar versiones de taxonomía de orquestadores

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Crear y activar versiones de la taxonomía de orquestadores  
**Para:** Evolucionar sus categorías sin romper el histórico

## Criterios de aceptación

- `POST /api/v1/admin/taxonomy/orchestrators/versions` crea una versión.
- `POST /api/v1/admin/taxonomy/orchestrators/versions/{id}/activate` la marca `is_current`.
- Es independiente de la taxonomía de modelos.
- Solo una versión puede ser `is_current` a la vez.
- La operación se registra en `AuditLog`.
