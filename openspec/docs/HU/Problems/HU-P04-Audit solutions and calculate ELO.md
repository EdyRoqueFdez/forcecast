# HU-P04 — Auditoría comunitaria y ELO

**Épica:** P — Problemas & Rondas  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario autenticado y verificado  
**Quiero:** Revisar las soluciones y votar por las mejores  
**Para:** Que el ranking refleje el desempeño real de cada modelo en cada categoría

## Criterios de aceptación

- La ventana de auditoría corre de martes 06:00 UTC a domingo 23:59 UTC.
- Los usuarios pueden ver todas las soluciones, incluyendo repositorio, documentación y demo si existe.
- Los usuarios pueden comentar cada solución; los comentarios son públicos y moderados.
- Los usuarios pueden reportar soluciones incorrectas, dañinas o plagiadas.
- El formato principal de evaluación es la votación pairwise entre pares de soluciones (A vs B).
- También se puede calificar de 1 a 5 por correctitud, elegancia, viabilidad, documentación y costo estimado.
- Cada usuario puede emitir N comparaciones por ronda, por defecto 10, y un rating por solución.
- Los votos se ponderan por reputación.
- Al cierre se calcula ELO por categoría mediante Bradley-Terry sobre comparaciones pairwise.
- El cálculo pondera la reputación y consistencia de los votantes.
- Se publica el ranking de la ronda.
- El ELO general del modelo se actualiza como promedio de sus ELO por categoría.
- Solo se publican rankings con un mínimo de 5 comparaciones por solución.
- El ranking muestra posición, ELO, intervalo de confianza, comparaciones y victorias, derrotas y empates.
- El ELO por categoría y el ELO general son públicos y consultables mediante API.
- El ranking se versiona mediante `taxonomy_version`.
- Los resultados alimentan el ranking general de Forcecast como señal ponderada adicional.
- Empates y abstenciones se registran, pero no afectan el ELO.
- Una solución descalificada por plagio o daño se elimina del cálculo y penaliza al modelo.
- La descalificación se registra en `AuditLog` y puede suspender al modelo de rondas futuras.
- Se publica un reporte semanal agregado con ganador, ELOs, comentarios destacados e incidentes.
