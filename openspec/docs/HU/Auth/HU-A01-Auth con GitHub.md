# HU-A01 — Auth con GitHub

**Épica:** A — Auth & Users  
**Sprint:** 1

## Historia de usuario

**Como:** Usuario de GitHub  
**Quiero:** Poder iniciar sesión en Forcecast  
**Para:** Poder emitir mis votos

## Criterios de aceptación

- Puedo autenticarme con OAuth2 vía GitHub.
- Si es mi primer login, se crea automáticamente mi `User` y `Profile`.
- Si ya existo, se reutiliza mi cuenta y se actualiza metadata de GitHub.
- Recibo cookie `httpOnly` + `Secure` + `SameSite=Lax` (web) o JWT en SecureStore (mobile).
- Si el OAuth falla, veo un mensaje de error claro y no se crea sesión.
