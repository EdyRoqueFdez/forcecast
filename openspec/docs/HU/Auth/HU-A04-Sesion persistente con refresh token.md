# HU-A04 — Sesión persistente con refresh token

**Épica:** A — Auth & Users  
**Sprint:** 1

## Historia de usuario

**Como:** Usuario autenticado  
**Quiero:** Que mi sesión se renueve sin volver a loguearme  
**Para:** No perder mi trabajo si el access token expira

## Criterios de aceptación

- Access token de vida corta (15 min) + refresh token de vida larga (30 días).
- El refresh ocurre de forma transparente en web y mobile.
- Si el refresh token expira o es revocado, se cierra sesión y se redirige al login.
- Los refresh tokens se almacenan hasheados en DB.
