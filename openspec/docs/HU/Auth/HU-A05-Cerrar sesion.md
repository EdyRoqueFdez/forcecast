# HU-A05 — Cerrar sesión

**Épica:** A — Auth & Users  
**Sprint:** 1

## Historia de usuario

**Como:** Usuario autenticado  
**Quiero:** Poder cerrar sesión en todos mis dispositivos  
**Para:** Proteger mi cuenta si pierdo un dispositivo

## Criterios de aceptación

- Puedo cerrar sesión solo en el dispositivo actual.
- Puedo cerrar sesión en todos los dispositivos (revoca refresh tokens).
- Se eliminan cookies/JWT locales.
- Se registra evento en `AuditLog`.
