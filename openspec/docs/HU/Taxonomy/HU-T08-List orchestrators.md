# HU-T08 — Listar orquestadores

**Épica:** T — Taxonomía  
**Sprint:** 0

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Ver los orquestadores disponibles  
**Para:** Saber sobre qué orquestadores puedo votar o consultar

## Criterios de aceptación

- `GET /api/v1/orchestrators` devuelve solo orquestadores con `status=approved`.
- Cada item incluye `slug`, nombre, descripción, `maintainer`, proveedores asociados, `website`, `repo_url`, versión y `status`.
- Se incluyen ejemplos como gentle-orchestrator, LangChain, LlamaIndex, AutoGen, CrewAI, Semantic Kernel, Haystack y DSPy.
- La respuesta es paginada y se ordena por nombre.
- Las descripciones se traducen a EN, ES, PT, FR y ZH.
- La respuesta se cachea durante un TTL configurable por endpoint, con valor por defecto de 60 segundos.
