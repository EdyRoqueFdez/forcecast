# HU-V07 — Ver ranking de orquestadores por categoría

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Ver el ranking agregado de orquestadores en una categoría  
**Para:** Decidir qué orquestador usar

## Criterios de aceptación

- `GET /api/v1/rankings/orchestrators?category=multi_agent&lang=es` devuelve el ranking.
- Se aplican las mismas reglas que en HU-V06, pero para orquestadores.
- Los rankings son independientes del ranking de modelos.
- Existe un endpoint combinado opcional: `GET /api/v1/rankings?scope=all`.
