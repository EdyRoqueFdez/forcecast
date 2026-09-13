# HU-T09 — Ver detalle de un orquestador

**Épica:** T — Taxonomía  
**Sprint:** 0

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Ver toda la información de un orquestador  
**Para:** Decidir si lo uso o lo voto

## Criterios de aceptación

- `GET /api/v1/orchestrators/{slug}` devuelve nombre, descripción, `maintainer`, versión, licencia, `website`, `repo_url`, proveedores asociados, categorías asociadas y `locale_used`.
- Si el slug no existe, devuelve `404`.
- No expone orquestadores en estado `pending_review`, `rejected` o `deprecated`.
- Un orquestador puede relacionarse con uno o varios proveedores.
