# HU-P01 — Subir un problema

**Épica:** P — Problemas & Rondas  
**Sprint:** 2

## Historia de usuario

**Como:** Usuario autenticado y verificado  
**Quiero:** Publicar un problema real de mi negocio o situación para que la comunidad y las IA lo aborden  
**Para:** Recibir soluciones auditables y contribuir a medir qué IA es mejor resolviendo problemas reales

## Criterios de aceptación

- Solo usuarios autenticados con email verificado pueden publicar.
- El formulario es estructurado, no PDF, y mobile-first.
- El formulario incluye título obligatorio de 10 a 120 caracteres.
- El dominio es obligatorio y se selecciona entre `healthcare`, `travel`, `finance`, `legal`, `retail`, `education`, `logistics` u `otro`.
- El subdominio es opcional y de texto libre.
- Es obligatorio indicar quién tiene el problema: persona, PyME, corporación, gobierno u ONG.
- La descripción del negocio/contexto es obligatoria y tiene entre 100 y 3000 caracteres.
- El país o región de operación es opcional.
- La escala (usuarios, transacciones o empleados) es opcional.
- Las regulaciones aplicables son opcionales.
- La descripción del problema es obligatoria y tiene entre 100 y 5000 caracteres.
- Son obligatorios: cómo se resuelve hoy, qué duele exactamente, a quién afecta, intentos previos, por qué fallaron, cómo se ve el éxito y KPIs medibles.
- Son opcionales: qué no quieren repetir, anti-requisitos, presupuesto, plazo, restricciones técnicas, restricciones legales/compliance y stack preferido o integraciones.
- Se pueden adjuntar hasta 5 archivos con un máximo total de 10 MB.
- La visibilidad del autor es obligatoria y permite `público`, `pseudónimo` o `anónimo`.
- Es obligatorio aceptar o rechazar la participación en rondas semanales.
- Es obligatorio aceptar o rechazar que las soluciones sean públicas.
- La validación server-side se realiza con Pydantic.
- El problema sigue el flujo `draft` -> `pending_review` -> `published`.
- Se aplica moderación automática de spam, toxicidad y PII, con revisión manual si hay flags.
- No se puede publicar con datos personales de terceros sin consentimiento.
- El problema queda asociado a la `taxonomy_version` vigente.
- El usuario puede editar mientras el problema está en `draft`.
- Después de publicar, cada edición crea una nueva versión y se registra en `AuditLog`.
- El problema no se borra; solo puede pasar a `archived` mediante soft delete.
- El rate limit es de un máximo de 3 problemas por semana y usuario.
- Las etiquetas visibles están internacionalizadas en EN, ES, PT, FR y ZH.
