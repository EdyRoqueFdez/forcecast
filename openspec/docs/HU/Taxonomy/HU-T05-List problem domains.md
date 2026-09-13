# HU-T05 — Listar dominios para problemas

**Épica:** T — Taxonomía  
**Sprint:** 0

## Historia de usuario

**Como:** Usuario o agente  
**Quiero:** Ver los dominios disponibles para clasificar problemas  
**Para:** Publicar problemas en la categoría correcta y consultar soluciones por industria

## Criterios de aceptación

- `GET /api/v1/domains` devuelve dominios activos.
- Los dominios base son `healthcare`, `travel`, `finance`, `legal`, `retail`, `education`, `logistics` y `other`.
- Cada dominio incluye `slug`, nombre traducido, descripción y subdominios opcionales.
- La jerarquía es de un nivel: dominio a subdominio.
- Se versiona con una TaxonomyVersion independiente de modelos y orquestadores.
- Se soporta i18n en EN, ES, PT, FR y ZH.
