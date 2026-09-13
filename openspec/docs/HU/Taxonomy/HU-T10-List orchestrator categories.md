# HU-T10 — Listar categorías de orquestadores

**Épica:** T — Taxonomía  
**Sprint:** 0

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Ver las categorías específicas de orquestadores  
**Para:** Votar y consultar rankings de orquestadores por capacidad

## Criterios de aceptación

- `GET /api/v1/categories?scope=orchestrators` devuelve las categorías propias de orquestadores.
- Las categorías base son `multi_agent`, `tool_use`, `planning`, `memory`, `rag`, `workflow`, `evaluation`, `routing`, `observability` y `cost_optimization`.
- Cada categoría tiene una `taxonomy_version` independiente de la taxonomía de modelos.
- Se traducen a EN, ES, PT, FR y ZH.
- La jerarquía es de un nivel.
