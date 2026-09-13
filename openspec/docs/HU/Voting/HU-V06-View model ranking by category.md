# HU-V06 — Ver ranking de modelos por categoría

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Ver el ranking agregado de modelos en una categoría  
**Para:** Decidir cuál usar o recomendar

## Criterios de aceptación

- `GET /api/v1/rankings/models?category=coding&lang=es` devuelve el ranking.
- La respuesta incluye modelo, votos ponderados, votos crudos, porcentaje del total, tendencia (7d/30d), `confidence`, `sample_size` y `taxonomy_version`.
- Solo aparecen modelos con el mínimo configurable de votos, por defecto 5.
- El resultado se ordena por votos ponderados descendentes.
- La respuesta incluye `locale_used`.
- El resultado se cachea durante 5 minutos.
- El resultado es paginado.
