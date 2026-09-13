# Notas técnicas de taxonomía

## Decisiones resueltas

- Se mantienen tres taxonomías independientes y versionadas: modelos, orquestadores y dominios.
- Las API keys de agentes existentes permanecen solo lectura. Las soluciones usarán una credencial separada con scope `write:solutions`.
- Los precios nulos se omiten en la API; no se añade `price_unknown`.
- Se mantienen los parámetros de la spec vigente: `provider_slug`, `modalities`, `category_slug`, `search` y `lang`.
- El TTL de caché es configurable por endpoint, con 60 segundos como valor base de la spec actual.
- Los nombres propios de proveedores no se traducen; las descripciones sí.
- Aprobar un modelo requiere al menos un `ModelHosting`.
- Un orquestador tiene un `maintainer` y puede funcionar con uno o varios proveedores.

## Dependencias

- `Orchestrator` y su relación many-to-many con `Provider`.
- `OrchestratorCategory` con taxonomía independiente.
- `Domain` y sus subdominios con taxonomía independiente.
- `AuditLog` para operaciones administrativas.
- Versionado atómico e inmutable para cada taxonomía.
