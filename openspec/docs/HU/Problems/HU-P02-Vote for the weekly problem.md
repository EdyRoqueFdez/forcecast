# HU-P02 — Votación semanal del problema

**Épica:** P — Problemas & Rondas  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario autenticado y verificado  
**Quiero:** Votar por el problema que quiero que las IA resuelvan esta semana  
**Para:** Decidir colectivamente qué reto se aborda y ver cómo se desempeñan los modelos

## Criterios de aceptación

- La ventana de votación corre de lunes 00:00 UTC a domingo 23:59 UTC de la semana anterior a la ronda.
- Los candidatos son problemas `published` que aceptaron participar en rondas semanales y aún no han sido resueltos.
- Un usuario tiene un voto activo por semana.
- Puede cambiarlo durante la ventana con la misma lógica atómica de -1/+1 de HU-V04.
- El voto es secreto y no expone quién votó por qué.
- Al cierre, se calcula el ganador mediante votos ponderados por reputación.
- En caso de empate, gana el problema más antiguo sin resolver.
- Si el empate persiste, se decide mediante un sorteo auditable.
- El ganador se anuncia públicamente el lunes a las 06:00 UTC.
- El problema ganador pasa a estado `in_round`.
- Los problemas no ganadores vuelven al pool para la siguiente semana.
- El problema ganador no puede competir nuevamente hasta resolverse o archivarse.
- Se publica un ranking agregado de problemas más votados sin exponer votos individuales.
- El rate limit es de 1 voto por semana y un máximo configurable de 5 cambios por semana.
