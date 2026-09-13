# HU-V02 — Emitir voto único por categoría para orquestadores

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario autenticado con GitHub  
**Quiero:** Votar por un orquestador en sus propias categorías  
**Para:** Que Forcecast también referencie la calidad de los orquestadores, no solo de los modelos base

## Criterios de aceptación

- Existe entidad `Orchestrator` (ej. gentle-orchestrator, LangChain, LlamaIndex, AutoGen, CrewAI, etc.).
- Existe `OrchestratorCategory` con su propio `taxonomy_version`.
- Un usuario tiene un único voto activo por categoría de orquestador.
- El voto referencia: `user_id`, `orchestrator_category_id`, `orchestrator_id`, `taxonomy_version`.
- Se aplican las mismas reglas de unicidad, verificación y ponderación que en HU-V01.
- Los rankings de modelos y orquestadores son independientes, pero consultables en conjunto.
