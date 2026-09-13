# HU-T11 — Filtrar orquestadores por categoría

**Épica:** T — Taxonomía  
**Sprint:** 0

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Ver orquestadores filtrados por categoría  
**Para:** Enfocarme en la capacidad que me interesa

## Criterios de aceptación

- `GET /api/v1/orchestrators?category=multi_agent` filtra por categoría.
- Si la categoría no existe, devuelve `404`.
- Si existe pero no hay orquestadores, devuelve `200` con una lista vacía.
- El filtro se puede combinar con búsqueda.
