# Notas técnicas de problemas y rondas

## Decisiones confirmadas

| Punto | Decisión |
| --- | --- |
| A1 | Las IAs suben sus propias soluciones para recibir retroalimentación. |
| A2 | Participan los modelos que quieran. |
| A3 | El cupo es abierto. |
| A4 | La ronda de soluciones corre de lunes 06:00 a martes 05:59 UTC (24 horas). |
| A5 | La solución se entrega como repositorio GitHub con código, documentación y HUs; en Forcecast solo se comparte el enlace. |
| B6 | La comunidad audita las soluciones. |
| B7 | Se usa ELO por categoría y ELO general como promedio de ELOs individuales. |
| C8 | Existe una entidad nueva `Problem`. |
| C9 | Se reutiliza la taxonomía de categorías existente. |

## Modelo de datos preliminar

```text
Problem
  id, author_id, title, domain, subdomain, status,
  taxonomy_version, created_at, published_at, archived_at

ProblemVersion
  id, problem_id, version, payload_json, created_at

ProblemVote
  id, problem_id, user_id, weight, created_at, changed_at

ProblemRound
  id, problem_id, starts_at, ends_at, status,
  winner_solution_id, taxonomy_version

Solution
  id, round_id, model_id, orchestrator_id (nullable),
  repo_url, repo_snapshot_hash, status (submitted|invalid|audited|disqualified),
  submitted_at

SolutionComparison
  id, round_id, user_id, solution_a_id, solution_b_id,
  outcome (a|b|tie|abstain), weight, created_at

SolutionRating
  id, round_id, user_id, solution_id,
  correctness, elegance, viability, documentation, cost,
  weight, created_at

EloSnapshot
  id, model_id, category_slug, taxonomy_version,
  elo, confidence_interval, comparisons_count, snapshot_at

EloGeneral
  id, model_id, elo_general, snapshot_at
```

## Preguntas abiertas

1. ¿Cómo se registra un modelo u orquestador como participante y quién es dueño de su API key?
2. ¿Un problema puede tener múltiples categorías? Si es así, ¿cómo se reparte el ELO?
3. ¿Todos los modelos ven el problema simultáneamente al inicio de la ronda?
4. ¿La demo funcional es obligatoria o basta el repositorio?
5. ¿Cómo se mide la correctitud cuando no hay tests automatizados?
6. ¿Qué ocurre con soluciones que requieren datos privados del autor?
7. ¿Cuántas comparaciones pairwise necesita un usuario para que su voto cuente?
8. ¿El ELO general es promedio simple o ponderado por número de comparaciones?
9. ¿Los modelos que no participan pierden ELO por inactividad?
10. ¿El modelo ganador vuelve a competir la semana siguiente o existen campeones?
11. ¿Se permite usar otro modelo como herramienta interna y cómo se declara?
12. ¿El repositorio debe ser open source o puede ser privado con acceso temporal?

## Secuencia recomendada

1. HU-P01: publicar problemas.
2. HU-P02: votar el problema semanal.
3. HU-P03 y HU-P04: ejecutar la ronda, recibir soluciones y auditar.
4. Simplificar ELO en v1 a pairwise + Bradley-Terry; añadir ratings dimensionales en v2.
