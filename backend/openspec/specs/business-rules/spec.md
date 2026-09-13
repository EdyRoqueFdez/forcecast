# Spec: Reglas de Negocio Generales

- Path: `backend/openspec/specs/business-rules/spec.md`
- Version: `1.0.0`
- Status: Draft
- Owner: Forcecast Core Team
- Last Updated: `2026-09-12`

## 1. Propósito

Esta spec define las reglas transversales de seguridad, privacidad, integridad del voto, operación, accesibilidad, dominio, moderación y cumplimiento legal de Forcecast. Las implementaciones que contradigan estas reglas MUST considerarse incompatibles con el dominio.

## 2. Convenciones

- `MUST` / `SHALL`: requisito obligatorio.
- `SHOULD`: recomendación que requiere justificación si no se aplica.
- `MAY`: comportamiento opcional.
- `N`: umbral configurable; su valor por defecto se indica cuando aplica.
- Los datos agregados MUST aplicar controles de privacidad antes de publicarse.

## 3. Reglas de negocio

### 3.1 Seguridad y acceso

#### RG-01 — Protección anti-scraping [Alta]

El sistema MUST proteger contenido, rankings y datos de votación contra extracción automatizada no autorizada, scraping masivo y uso comercial no licenciado, sin degradar la experiencia de usuarios humanos legítimos.

- MUST aplicar límites por IP, device fingerprint y cuenta: 60 req/min para usuarios autenticados, 20 req/min para anónimos y 5 req/min para endpoints sensibles.
- MUST detectar user-agents sospechosos, headers ausentes, requests sin recursos estáticos, timing uniforme y navegación secuencial por IDs.
- MUST usar Turnstile, WAF/Bot Management, honeypots y bloqueo progresivo cuando corresponda.
- MUST exigir paginación, máximo 100 resultados por request y MUST NOT exponer endpoints dump.
- MUST exigir API keys con cuotas para acceso programático y firma HMAC con timestamp en endpoints de agentes.
- MUST registrar alertas de scraping y aplicar 429, 403, ban temporal o ban permanente según severidad.
- MUST proteger imágenes y avatares con URLs firmadas con expiración.
- Los buscadores verificados MAY indexar únicamente páginas públicas de marketing.

**Escenario:** Given un cliente supera el límite o presenta patrones automatizados, When solicita un endpoint protegido, Then el sistema MUST aplicar el desafío, límite o bloqueo correspondiente y registrar el evento.

#### RG-02 — Privacidad del voto [Alta]

La identidad, voto individual, historial, comentario y metadata asociada MUST ser privados por defecto. Solo se expondrán agregados que no permitan reidentificación.

- Los rankings agregados MAY ser públicos, pero los votos individuales MUST NOT exponerse por defecto.
- Los agregados públicos MUST cumplir k-anonimidad con mínimo N=10 votos por categoría y MUST suprimir celdas con menos de 5 votos.
- Los comentarios solo serán públicos con perfil `público`; con perfil `pseudónimo` no se vincularán a la identidad.
- El historial individual solo será accesible por el propio usuario.
- IP, device fingerprint y geolocalización aproximada MUST NOT exponerse por API.
- `AuditLog` MUST ser interno y accesible solo a admins autorizados.
- El usuario MUST poder exportar y solicitar el borrado de sus datos.
- Los campos sensibles MUST cifrarse en reposo y todo tráfico MUST usar TLS 1.3 o superior.
- El `user_id` interno MUST NOT exponerse; las APIs usarán `public_id` y username opcional.

**Escenario:** Given un ranking con menos del umbral de privacidad, When un cliente solicita el ranking público, Then el sistema MUST devolver datos insuficientes u ocultar la celda pequeña.

#### RG-03 — Autenticación obligatoria para votar [Alta]

Solo usuarios autenticados, con email verificado y sin señales activas de bot MUST poder votar, comentar o cambiar votos.

#### RG-04 — Principio de mínimo privilegio [Alta]

Los roles anónimo, usuario, usuario verificado, admin y agente MUST tener permisos explícitos. Ningún rol MUST recibir permisos implícitos.

#### RG-05 — API keys de agentes solo lectura [Alta]

Las API keys de agentes MUST limitarse a consultas autorizadas de rankings y modelos. Votar, comentar o modificar datos con una API key MUST devolver `403 Forbidden` y registrar un evento.

#### RG-06 — Rotación de secretos [Media]

API keys, refresh tokens y secretos HMAC MUST expirar, poder rotarse sin downtime y revocarse inmediatamente si se comprometen.

#### RG-07 — Auditoría inmutable [Alta]

Toda acción sensible MUST registrarse en un `AuditLog` append-only con actor, acción, timestamp, request_id y origen. Incluye login, votos, cambios, aprobaciones, cambios de taxonomía y revocaciones.

### 3.2 Integridad del voto

#### RG-08 — Un voto activo por usuario y categoría [Alta]

Un usuario MUST tener exactamente un voto activo por categoría de modelo y uno por categoría de orquestador. Cambiar el voto MUST aplicar -1 al anterior y +1 al nuevo de forma atómica.

#### RG-09 — Transaccionalidad del cambio [Alta]

Un cambio de voto MUST ser atómico. Si falla cualquier paso, no se aplicará ningún ajuste y MUST NOT existir doble conteo.

#### RG-10 — Ponderación por reputación y anti-abuso [Alta]

Cada voto MUST ponderarse por reputación, antigüedad, consistencia y señales anti-bot. Usuarios con peso 0 MAY continuar votando, pero sus votos MUST tener impacto sombra y no afectar el ranking.

#### RG-11 — Umbral mínimo para publicar rankings [Alta]

Un modelo u orquestador MUST tener al menos N votos ponderados, por defecto 5, para aparecer en rankings públicos. Antes de ese umbral MUST mostrarse como datos insuficientes.

#### RG-12 — Ventanas temporales de tendencia [Media]

Los rankings MUST exponer tendencia a 7 días, 30 días y all-time. Los snapshots publicados MUST ser inmutables.

#### RG-13 — Histórico append-only [Alta]

Cambiar un voto MUST NOT borrar eventos anteriores. `VoteEvent` MUST ser append-only y el estado actual MUST derivarse del último evento válido.

#### RG-14 — Revocación controlada [Media]

El usuario MAY cambiar su voto y MUST poder revocarlo sin seleccionar otro. `revoke` aplica -1 al target actual y deja la categoría sin voto activo.

#### RG-15 — Detección de colusión [Alta]

El sistema MUST detectar cuentas coordinadas mediante ventanas temporales, device fingerprints e IPs relacionadas. Las cuentas detectadas MUST excluirse del ranking o marcarse para revisión según la política vigente.

**Escenario:** Given varias cuentas votan por el mismo target en una ventana anómala y comparten fingerprint, When el detector confirma el patrón, Then sus pesos MUST reducirse o excluirse y MUST registrarse el caso.

### 3.3 Datos y privacidad

#### RG-16 — Minimización de datos [Alta]

El sistema MUST recolectar únicamente datos necesarios para el propósito declarado y MUST NOT almacenar datos por si acaso.

#### RG-17 — Retención limitada [Alta]

Los datos personales MUST retenerse mientras la cuenta esté activa y como máximo 24 meses tras su última actividad; después MUST anonimizarse o eliminarse. `AuditLog` se retendrá 5 años por compliance.

#### RG-18 — Derecho al olvido [Alta]

El usuario MUST poder solicitar el borrado completo. Sus votos MUST anonimizarse en agregados históricos y eliminarse de rankings futuros. El proceso MUST ser auditable.

#### RG-19 — Portabilidad [Media]

El usuario MUST poder exportar perfil, votos, comentarios e historial en JSON o CSV legible.

#### RG-20 — Consentimiento granular [Alta]

Prompt completo, metadata de uso y perfil público MUST requerir consentimientos independientes, explícitos y revocables.

#### RG-21 — Anonimización antes de análisis [Alta]

La investigación, ML y reportes MUST usar datos anonimizados o agregados y MUST NOT usar datos crudos identificables.

#### RG-22 — GDPR, CCPA y legislación aplicable [Alta]

Forcecast MUST soportar los derechos aplicables de GDPR, CCPA y leyes de Puerto Rico mediante endpoints dedicados o un canal de privacidad.

### 3.4 Accesibilidad e internacionalización

#### RG-23 — Internacionalización obligatoria [Alta]

Todo texto visible MUST pasar por el sistema de traducción. Los idiomas soportados son EN, ES, PT, FR y ZH. No se permiten strings visibles hardcodeados.

#### RG-24 — Fallback de idioma [Alta]

Si falta una traducción, MUST servirse EN; si también falta EN, MUST servirse el `display_name` base. La respuesta MUST indicar `locale_used`.

#### RG-25 — WCAG 2.2 AA [Alta]

Web y mobile MUST cumplir WCAG 2.2 AA, incluyendo contraste, teclado, lectores de pantalla y targets táctiles mínimos de 44x44 px.

#### RG-26 — Mobile-first [Alta]

La experiencia MUST diseñarse primero para mobile y validarse en dispositivos reales antes de adaptar breakpoints a desktop.

### 3.5 Operación y calidad

#### RG-27 — Disponibilidad objetivo [Media]

La API pública SHOULD alcanzar 99.9% de disponibilidad mensual. Mantenimientos planificados SHOULD anunciarse con 72 horas de antelación.

#### RG-28 — Performance objetivo [Alta]

El sistema SHOULD mantener p95 menor de 200 ms para listados, 500 ms para rankings y 1 s para recomendaciones.

#### RG-29 — Idempotencia en operaciones críticas [Alta]

Votos, cambios, ingestas y aprobaciones MUST ser idempotentes. Reintentar una operación MUST NOT duplicar ni corromper datos.

#### RG-30 — Observabilidad [Alta]

Toda request MUST tener `request_id`. Los logs MUST ser JSON estructurado, las métricas MUST estar disponibles en Prometheus/Grafana y los errores MUST llegar a Sentry con contexto.

#### RG-31 — Feature flags [Media]

Las funciones nuevas, incluyendo ingesta, votación de orquestadores y MCP, MUST poder desplegarse detrás de feature flags de PostHog.

#### RG-32 — Backups y recuperación [Alta]

PostgreSQL MUST tener backups diarios con retención de 30 días, RPO menor o igual a 1 hora y RTO menor o igual a 4 horas. La restauración MUST probarse trimestralmente.

#### RG-33 — Versionado de API [Alta]

La API pública MUST versionarse como `/api/v1/`. Los cambios breaking MUST usar una nueva versión y un periodo de deprecación de 6 meses.

#### RG-34 — Contratos versionados [Alta]

El contrato OpenAPI MUST publicarse en `forcecast/contracts`. Los cambios breaking MUST disparar regeneración de clientes web y mobile.

### 3.6 Integridad del dominio

#### RG-35 — Taxonomía versionada [Alta]

Los cambios de categorías MUST crear una nueva `TaxonomyVersion`. Todo voto MUST referenciar la versión vigente al emitirse y los rankings históricos MUST ser reproducibles.

#### RG-36 — Solo modelos aprobados son votables [Alta]

El sistema MUST impedir votos sobre modelos en estado `draft`, `pending_review`, `rejected` o `deprecated`.

#### RG-37 — Modelos deprecados fuera del ranking activo [Media]

Un modelo deprecated MUST salir de rankings activos, pero su historial MUST conservarse para consulta autorizada.

#### RG-38 — Trazabilidad de fuente [Media]

Todo modelo y orquestador MUST tener `source`, `source_url` y `source_payload_hash` auditables.

#### RG-39 — Separación de modelos y orquestadores [Alta]

Rankings, endpoints y taxonomías de modelos y orquestadores MUST ser independientes. Un usuario MAY votar en ambos sin conflicto.

#### RG-40 — Neutralidad del ranking [Alta]

Forcecast MUST calcular rankings únicamente con votos ponderados y reglas públicas, sin favorecer proveedores. Todo cambio de algoritmo MUST documentarse y anunciarse.

### 3.7 Moderación y contenido

#### RG-41 — Moderación de comentarios [Alta]

Los comentarios MUST pasar por filtro automático de spam y toxicidad, reportes de usuarios y revisión manual. El contenido removido MUST registrarse en `AuditLog`.

#### RG-42 — Apelación [Media]

El usuario MUST poder apelar una sanción o remoción. Las apelaciones SHOULD revisarse en un máximo de 7 días.

#### RG-43 — Transparencia de moderación [Media]

Forcecast SHOULD publicar un reporte trimestral agregado de reportes, acciones y apelaciones sin datos personales.

#### RG-44 — Prohibición de contenido ilegal [Alta]

Contenido ilegal, amenazas o doxxing MUST removerse inmediatamente y MUST reportarse a las autoridades cuando la ley lo requiera.

### 3.8 Comercial y legal

#### RG-45 — Sin venta de datos [Alta]

Forcecast MUST NOT vender datos de usuarios a terceros.

#### RG-46 — Licencia de agregados [Media]

Rankings agregados y anonimizados SHOULD publicarse bajo una licencia abierta como CC BY 4.0, con atribución a Forcecast.

#### RG-47 — Términos de servicio claros [Alta]

Los TOS y la Política de Privacidad MUST existir en EN, ES, PT, FR y ZH, con changelog y fecha de vigencia.

#### RG-48 — Edad mínima [Media]

La plataforma MUST aplicar una edad mínima de 16 años bajo GDPR o de 13 años con consentimiento parental bajo COPPA, según jurisdicción.

## 4. Escenarios transversales

### 4.1 Voto rechazado por identidad o estado

**Given** un usuario anónimo, no verificado, marcado como bot o un modelo no aprobado  
**When** intenta emitir o cambiar un voto  
**Then** la API MUST rechazar la operación, no modificar rankings y registrar el motivo en `AuditLog`.

### 4.2 Cambio idempotente y transaccional

**Given** un usuario con un voto activo y una solicitud de cambio con clave de idempotencia  
**When** la solicitud se procesa una o varias veces  
**Then** solo debe existir un `VoteEvent` efectivo, el anterior recibe -1, el nuevo +1 y una falla parcial MUST revertir toda la transacción.

### 4.3 Eliminación de cuenta

**Given** un usuario solicita el derecho al olvido  
**When** la solicitud es validada y ejecutada  
**Then** sus datos identificables MUST eliminarse o anonimizarse, los agregados históricos MUST conservarse solo de forma no reidentificable y la operación MUST quedar auditada.

### 4.4 Fallback de locale

**Given** una solicitud con un locale soportado que no tiene traducción  
**When** se construye la respuesta  
**Then** se MUST usar EN, después el `display_name` base, y MUST incluirse `locale_used`.

## 5. MVP: reglas no negociables

El MVP MUST priorizar estas diez reglas:

1. RG-01 — Protección anti-scraping.
2. RG-02 — Privacidad del voto.
3. RG-03 — Autenticación obligatoria para votar.
4. RG-08 — Un voto por usuario y categoría.
5. RG-09 — Transaccionalidad del cambio.
6. RG-10 — Ponderación por reputación.
7. RG-15 — Detección de colusión.
8. RG-18 — Derecho al olvido.
9. RG-35 — Taxonomía versionada.
10. RG-40 — Neutralidad del ranking.

Las reglas restantes MAY incorporarse progresivamente, pero ninguna implementación SHOULD degradar las garantías de privacidad, integridad y neutralidad definidas aquí.
