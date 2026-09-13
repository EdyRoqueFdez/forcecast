# HU-V09 — Detección de fanboys y votos anómalos

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Sistema Forcecast  
**Quiero:** Detectar usuarios que votan siempre por el mismo modelo/orquestador  
**Para:** Evitar sesgo en el ranking

## Criterios de aceptación

- Se detecta que más del 90% de los votos se dirigen al mismo target en todas las categorías.
- Se detectan ráfagas de más de 30 votos por minuto o más de 10 cambios por hora.
- Se detecta el mismo device fingerprint en múltiples cuentas.
- Se detectan cambios de voto en intervalos sospechosamente cortos, inferiores a 1 minuto.
- Los usuarios detectados tienen peso reducido o quedan excluidos del ranking.
- Se registra el evento en `AuditLog`.
