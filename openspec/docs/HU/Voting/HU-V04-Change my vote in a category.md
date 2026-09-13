# HU-V04 — Cambiar mi voto en una categoría

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario autenticado  
**Quiero:** Cambiar mi voto cuando pruebo un modelo/orquestador mejor  
**Para:** Que mi opinión refleje siempre mi experiencia actual

## Criterios de aceptación

- `POST /api/v1/votes/{category_id}/change` acepta `{target_id, comment?}`.
- Si ya tenía voto en esa categoría, el modelo anterior recibe -1 (ponderado) y el modelo nuevo recibe +1 (ponderado).
- Se registra `VoteEvent` tipo `change` con `previous_target_id` y `new_target_id`.
- El `UserCategoryPreference` se actualiza al nuevo target.
- El histórico completo queda en `VoteEvent` (append-only).
- El ranking se recalcula de forma consistente, sin doble conteo.
- Si intento cambiar al mismo modelo, devuelve `204 No Content` (idempotente).
- El cambio es transaccional: se aplican ambos ajustes o ninguno.
- La respuesta incluye el nuevo estado del ranking.
- El rate limit es de un máximo de 10 cambios por hora y usuario (configurable).
