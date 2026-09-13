# HU-A09 — API keys para agentes (solo lectura)

**Épica:** A — Auth & Users  
**Sprint:** 1

## Historia de usuario

**Como:** Desarrollador de gentle-orchestrator  
**Quiero:** Generar API keys para que mis agentes consulten Forcecast  
**Para:** Que los agentes lean rankings sin poder votar

## Criterios de aceptación

- Puedo crear/revocar API keys desde mi perfil.
- Las keys solo tienen permisos de lectura (`read:recommendations`, `read:models`).
- Intentar votar con una API key devuelve `403 Forbidden`.
- Las keys se almacenan hasheadas.
- Puedo ver último uso y expiración.
