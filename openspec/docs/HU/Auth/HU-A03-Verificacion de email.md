# HU-A03 — Verificación de email

**Épica:** A — Auth & Users  
**Sprint:** 1

## Historia de usuario

**Como:** Usuario recién registrado  
**Quiero:** Verificar mi correo electrónico  
**Para:** Confirmar que soy humano y desbloquear la votación

## Criterios de aceptación

- Al registrarme recibo un email con enlace de verificación (expira en 24 h).
- No puedo votar hasta verificar.
- Puedo reenviar el email (máx. 3 veces/hora).
- Al verificar, mi `User.email_verified = true` y se registra timestamp.
- Si el enlace expira, puedo solicitar uno nuevo.
