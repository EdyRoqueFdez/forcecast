# HU-A10 — Rate limiting por usuario/IP

**Épica:** A — Auth & Users  
**Sprint:** 1

## Historia de usuario

**Como:** Sistema Forcecast  
**Quiero:** Limitar la frecuencia de acciones sensibles  
**Para:** Prevenir abuso y ataques

## Criterios de aceptación

- Límites por defecto: 60 req/min por usuario, 20 req/min por IP anónima.
- Login: 5 intentos/min por IP.
- Votos: 30/min por usuario.
- Al exceder, se devuelve `429 Too Many Requests` con `Retry-After`.
- Se registra en `AuditLog`.
