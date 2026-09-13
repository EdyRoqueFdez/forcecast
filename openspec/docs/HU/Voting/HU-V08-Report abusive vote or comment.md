# HU-V08 — Reportar voto o comentario abusivo

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario autenticado  
**Quiero:** Reportar votos o comentarios spam/abusivos  
**Para:** Mantener la calidad del ranking

## Criterios de aceptación

- Existe un botón para reportar cada comentario y perfil de voto.
- Las razones disponibles son: spam, ofensivo, falso, duplicado y otro.
- Se crea un `Report` con estado `pending`.
- Un administrador revisa el reporte.
- Si se confirma, se ajusta la reputación del autor y se recalcula el ranking.
