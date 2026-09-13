# HU-V12 — Ponderación del voto por reputación

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Sistema Forcecast  
**Quiero:** Ponderar cada voto según la reputación del usuario  
**Para:** Que la opinión de usuarios expertos pese más

## Criterios de aceptación

- `weight = f(reputation, antigüedad, consistencia, actividad)`.
- Un usuario nuevo tiene un peso base, por ejemplo 0.5.
- Un usuario verificado con historial tiene un peso de hasta 2.0.
- Un usuario detectado como bot/fanboy tiene peso 0.
- El peso se calcula al emitir el voto y se guarda en `VoteEvent` para auditoría.
- Los cambios de reputación no recalculan votos pasados automáticamente; se aplican en el próximo recálculo batch.
