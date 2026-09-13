# HU-AT07 — Gestionar versiones de dominios de problemas

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Crear y activar versiones de dominios  
**Para:** Evolucionar los dominios de problemas sin romper el histórico

## Criterios de aceptación

- `POST /api/v1/admin/taxonomy/domains/versions` crea una versión.
- `POST /api/v1/admin/taxonomy/domains/versions/{id}/activate` la marca `is_current`.
- Es independiente de las taxonomías de modelos y orquestadores.
- Solo una versión puede ser `is_current` a la vez.
- La operación se registra en `AuditLog`.
