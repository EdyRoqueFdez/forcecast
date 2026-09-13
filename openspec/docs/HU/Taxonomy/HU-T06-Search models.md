# HU-T06 — Buscar modelos

**Épica:** T — Taxonomía  
**Sprint:** 0

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Buscar modelos por nombre o familia  
**Para:** Encontrarlos rápido

## Criterios de aceptación

- `GET /api/v1/models?q=claude` busca de forma case-insensitive en `slug`, `display_name` y `family`.
- Los resultados se ordenan por relevancia.
- Si no hay resultados, devuelve `200` con lista vacía y `total: 0`.
- La búsqueda se puede combinar con `provider_slug`, `modalities` y `category_slug`.
