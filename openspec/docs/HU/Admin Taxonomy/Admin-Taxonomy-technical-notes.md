# Notas técnicas de administración de taxonomía

## Alcance

Este conjunto cubre aprobación e ingesta de modelos, gestión de proveedores, orquestadores, categorías y dominios, traducciones y auditoría.

## Decisiones aplicadas

- Se mantienen tres taxonomías independientes y versionadas: modelos, orquestadores y dominios.
- Las API keys de agentes de HU-A09 siguen siendo solo lectura.
- Las soluciones de rondas usan una credencial separada con `write:solutions`.
- Aprobar un modelo requiere al menos un `ModelHosting`.
- Un orquestador tiene `maintainer` y relación many-to-many con proveedores.
- Los nombres propios de proveedores no se traducen; las descripciones sí.
- Las versiones históricas son inmutables y las activaciones son atómicas.
- Toda mutación administrativa se registra en `AuditLog`.
