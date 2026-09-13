# HU-V01 — Emitir voto único por categoría para modelos IA

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario autenticado con GitHub  
**Quiero:** Votar por un modelo IA en cada categoría  
**Para:** Que mi experiencia alimente la referencia de la industria sobre fortalezas y debilidades de cada modelo

## Criterios de aceptación

- Solo usuarios autenticados y verificados pueden votar.
- Un usuario tiene un único voto activo por categoría.
- El voto referencia: `user_id`, `category_id`, `model_id`, `taxonomy_version`.
- Si ya voté en esa categoría, la API devuelve `409 Conflict` con instrucción de usar el endpoint de cambio de voto.
- El voto se registra como `VoteEvent` (tipo `cast`).
- El ranking agregado se actualiza: modelo elegido +1 (ponderado por reputación).
- La respuesta incluye el estado actualizado del ranking para esa categoría.
- No puedo votar por un modelo con `status != approved`.
- No puedo votar en una categoría inexistente o inactiva.
