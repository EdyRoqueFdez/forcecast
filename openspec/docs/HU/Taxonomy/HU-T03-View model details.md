# HU-T03 — Ver detalle de un modelo

**Épica:** T — Taxonomía  
**Sprint:** 0

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Ver toda la información de un modelo  
**Para:** Decidir si lo uso o lo voto

## Criterios de aceptación

- `GET /api/v1/models/{slug}` devuelve proveedor, familia, versión, modalidad, contexto, precios, fechas, categorías asociadas, descripción traducida, `source` y `source_url`.
- Los precios se serializan como strings decimales, nunca como float.
- Si no hay precio, los campos de precio se omiten completamente.
- La respuesta incluye `locale_used`.
- Si el slug no existe, devuelve `404`.
