# Notas técnicas de votación

## Dependencias bloqueantes

1. Nueva entidad `Orchestrator` en taxonomía (Sprint 0).
2. Nueva entidad `OrchestratorCategory` con su propio `taxonomy_version`.
3. Nuevo tipo de `VoteEvent`: `cast`, `change`, `revoke`.
4. Nuevo `UserCategoryPreference` con FK a `model_id` o `orchestrator_id` (polymorphic).
5. El scoring cambia de Elo/pairwise a conteo agregado ponderado más ventana temporal.
6. Se necesitan snapshots para las ventanas de tendencia de 7 días, 30 días y all-time.

## Nota técnica sobre el scoring

El modelo de un voto por categoría es más simple y explicable que pairwise, pero pierde información de comparación: si dos modelos son buenos, no muestra cuál es mejor, solo cuál fue elegido.

Como mitigación, se puede permitir un up/down rápido y un rating de 1 a 5 por dimensión como señales secundarias opcionales. No reemplazan el voto principal y enriquecen el scoring sin romper la regla de unicidad.
