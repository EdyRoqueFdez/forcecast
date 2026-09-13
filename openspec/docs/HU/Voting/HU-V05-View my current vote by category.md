# HU-V05 — Ver mi voto actual por categoría

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario autenticado  
**Quiero:** Ver en qué modelo/orquestador voté en cada categoría  
**Para:** Recordar y gestionar mis preferencias

## Criterios de aceptación

- `GET /api/v1/me/votes?type=model|orchestrator` devuelve mis votos.
- La respuesta incluye categoría, target actual, fecha del voto, comentario y `taxonomy_version`.
- El resultado es paginado.
- Si no he votado en una categoría, no aparece o aparece con `voted: false` cuando se solicita `include_empty=true`.
