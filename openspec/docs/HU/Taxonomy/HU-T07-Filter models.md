# HU-T07 — Filtrar modelos por categoría, proveedor y modalidad

**Épica:** T — Taxonomía  
**Sprint:** 0

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Filtrar modelos por múltiples criterios  
**Para:** Reducir opciones según mis restricciones

## Criterios de aceptación

- `GET /api/v1/models?category_slug=coding&provider_slug=anthropic&modalities=vision` filtra por los criterios indicados.
- Múltiples valores de `modalities` se tratan como OR.
- Múltiples valores de `category_slug` se tratan como OR.
- Los filtros se pueden combinar con búsqueda.
- El resultado es paginado.
- La metadata de respuesta incluye todos los filtros aplicados.
