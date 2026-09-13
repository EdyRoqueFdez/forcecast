# HU-V11 — Consultar el voto de otro usuario (si es público)

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario autenticado  
**Quiero:** Ver los votos públicos de otros usuarios  
**Para:** Conocer la opinión de referentes de la comunidad

## Criterios de aceptación

- Solo se muestran votos si el perfil del otro usuario es `público`.
- `GET /api/v1/users/{username}/votes` devuelve los votos autorizados.
- No se exponen datos privados como email, IP o device.
- Se respeta la configuración de privacidad del propietario del perfil.
