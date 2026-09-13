# HU-T04 — Listar categorías de modelos

**Épica:** T — Taxonomía  
**Sprint:** 0

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Ver las categorías de modelos disponibles  
**Para:** Saber en qué tareas puedo votar o consultar

## Criterios de aceptación

- `GET /api/v1/categories?scope=models` devuelve categorías `active` de la TaxonomyVersion actual de modelos.
- Incluye la jerarquía mediante `parent_slug`.
- Incluye `taxonomy_version` en la respuesta.
- Las categorías se traducen según `lang`, con fallback a EN.
- Incluye las 17 categorías base definidas por la taxonomía de modelos.
