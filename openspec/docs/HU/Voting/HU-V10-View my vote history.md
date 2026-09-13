# HU-V10 — Ver mi historial de votos

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario autenticado  
**Quiero:** Ver todos mis votos y cambios  
**Para:** Auditar mi propia contribución

## Criterios de aceptación

- `GET /api/v1/me/votes/history` devuelve mi historial.
- La lista incluye `VoteEvent` con timestamp, tipo (`cast`, `change`), target anterior, target nuevo, categoría y comentario.
- Puedo filtrar por categoría, target, fecha y tipo.
- El resultado es paginado.
- Puedo exportar el historial a JSON o CSV.
