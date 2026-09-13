# HU-A08 — CAPTCHA en registro y votos sospechosos

**Épica:** A — Auth & Users  
**Sprint:** 1

## Historia de usuario

**Como:** Sistema Forcecast  
**Quiero:** Desafiar con Turnstile en puntos críticos  
**Para:** Evitar bots y votos automatizados

## Criterios de aceptación

- Turnstile se muestra en: registro, primer voto, votos en ráfaga.
- Si falla, se bloquea la acción y se registra en `AuditLog`.
- No afecta la experiencia de usuarios normales (invisible o mínimo).
- Configurable por feature flag (PostHog).
