# HU-V03 — Dejar opinión/comentario opcional en el voto

**Épica:** V — Votación & Opiniones  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario autenticado  
**Quiero:** Adjuntar un comentario a mi voto  
**Para:** Explicar por qué elegí ese modelo/orquestador

## Criterios de aceptación

- El comentario es opcional.
- La longitud permitida es de 0 a 1000 caracteres.
- Soporta texto plano (markdown básico opcional).
- Se guarda asociado al `VoteEvent`.
- Puedo editar mi comentario mientras mi voto esté activo.
- El comentario hereda el nivel de privacidad de mi perfil (`pseudónimo` o `público`).
- Se aplica moderación (reportes y detección de spam).
- Se registra cualquier edición en `AuditLog`.
