# HU-A02 — Auth con Google

**Épica:** A — Auth & Users  
**Sprint:** 1

## Historia de usuario

**Como:** Usuario con cuenta Google  
**Quiero:** Poder iniciar sesión en Forcecast  
**Para:** No tener que crear credenciales nuevas

## Criterios de aceptación

- Mismo flujo que HU-A01 pero con OAuth2 Google.
- Si el email de Google coincide con un usuario GitHub existente, se vinculan cuentas (si el usuario lo autoriza).
- Si no autoriza, se crea cuenta separada.
