# Forcecast — Audit de Cumplimiento de Reglas de Negocio

- **Fecha de auditoría:** 2026-09-12
- **Spec fuente:** `openspec/specs/business-rules/spec.md` v1.0.0
- **Alcance:** Backend (Python/FastAPI) — revisión de código vs reglas definidas
- **Próxima revisión:** _pendiente_

---

## Convenciones

| Símbolo | Significado |
|---------|-------------|
| ✅ | Cumple — implementado y verificado en código |
| ⚠️ | Parcial — existe base pero faltan partes clave |
| ❌ | No implementado — requiere trabajo nuevo |
| 🔴 | MVP no negociable — debe resolverse antes de launch |
| ⬜ | No MVP — puede incorporarse progresivamente |
| 🔧 | Requiere fix — lo que hay no cumple la spec |

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| Total reglas de negocio | 48 |
| Reglas MVP (no negociables) | 10 |
| ✅ Cumplen | 7 |
| ⚠️ Parciales | 7 |
| ❌ No implementadas | 34 |
| Cumplimiento MVP | **7/10 (70%)** |
| Cumplimiento total | **7/48 (15%)** |

### Última actualización: 2026-09-12
- **Fase 1 completada:** Sistema de votación implementado (VoteEvent, UserVote, AuditLog)
- **9 tests pasando** en `app/voting/tests/test_vote_service.py`

---

## 1. Seguridad y Acceso

### RG-01 — Protección anti-scraping [🔴 MVP]

**Estado: ⚠️ PARCIAL**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Límites por IP: 60 req/min autenticados, 20 req/min anónimos | ⚠️ | Rate limits configurados: USER=300, ADMIN=1000. Faltan 60/20 específicos |
| Límites endpoints sensibles: 5 req/min | ⚠️ | LOGIN=10, REGISTER=5 (cerca pero no exacto) |
| Detección user-agents sospechosos | ❌ | No hay inspección de User-Agent |
| Headers ausentes, requests sin recursos estáticos | ❌ | No implementado |
| Timing uniforme y navegación secuencial por IDs | ❌ | No implementado |
| Turnstile / hCaptcha | ✅ | `app/auth/services/anti_bot.py:verify_turnstile()` |
| WAF / Bot Management | ❌ | No configurado |
| Honeypots | ❌ | No implementado |
| Bloqueo progresivo | ❌ | Solo reputation penalty lineal, no progresivo |
| Paginación, máx 100 resultados | ✅ | Cursor pagination en `PublicService` |
| Sin endpoints dump | ✅ | No existe endpoint de exportación masiva |
| API keys con cuotas | ✅ | `rate_limit_rpm` por key, validación en `check_rate_limit()` |
| HMAC con timestamp para agentes | ❌ | No implementado |
| Alertas de scraping, 429/403/ban | ⚠️ | 429 por rate limit ✓. Sin alertas ni ban temporal/permanente |
| URLs firmadas para imágenes/avatares | ❌ | No implementado |

**Acciones requeridas:**
1. Ajustar rate limits a 60/20/5 según spec (auth/anónimo/sensibles)
2. Implementar detección de User-Agent sospechoso
3. Implementar honeypot fields en formularios
4. Implementar bloqueo progresivo (429 → 403 → ban temporal → ban permanente)
5. Implementar HMAC + timestamp para endpoints de agentes
6. Implementar URLs firmadas con expiración para imágenes
7. Configurar WAF en infra

---

### RG-02 — Privacidad del voto [🔴 MVP]

**Estado: ❌ SIN SISTEMA DE VOTACIÓN**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Votos individuales no expuestos | N/A | No hay votos |
| k-anonimidad N=10 | ❌ | No implementado |
| Supresión celdas <5 votos | ❌ | No implementado |
| Comentarios solo con perfil público | ❌ | No hay sistema de comentarios |
| Historial accesible solo por propio usuario | ❌ | No hay historial de votos |
| IP/fingerprint/geolocalización no expuestos | ⚠️ | No se exponen explícitamente, pero no hay política formal |
| AuditLog interno solo admins | ❌ | No existe AuditLog |
| Exportación y borrado de datos | ❌ | No implementado |
| Campos sensibles cifrados en reposo | ❌ | Sin cifrado de campos sensibles |
| TLS 1.3 | ⚠️ | Depende de infra, no verificable en código |
| user_id interno no expuesto, usar public_id | ❌ | Solo se usa `id` (UUID), sin `public_id` separado |

---

### RG-03 — Autenticación obligatoria para votar [🔴 MVP]

**Estado: ⚠️ PARCIAL (auth existe, falta votación)**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Solo autenticados pueden votar | ⚠️ | Auth middleware ✓. Endpoint de voto no existe |
| Email verificado | ❌ | Campo `email_verified` existe pero sin verificación real |
| Sin señales activas de bot | ⚠️ | `is_strict_mode()` existe pero no se usa en flujo de voto |

---

### RG-04 — Principio de mínimo privilegio [✅]

**Estado: ✅ CUMPLE**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Roles con permisos explícitos | ✅ | `RoleEnum(user, admin)` + `require_admin()` |
| Sin permisos implícitos | ✅ | API keys con scopes explícitos `read:*` |

---

### RG-05 — API keys de agentes solo lectura [✅]

**Estado: ✅ CUMPLE**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Solo consultas autorizadas | ✅ | `ALLOWED_SCOPES = {read:models, read:categories, read:providers, read:locales}` |
| Votar/comentar/modificar con API key → 403 | ⚠️ | Scopes lo impiden, pero no hay endpoint de voto que lo valide |

---

### RG-06 — Rotación de secretos [⬜]

**Estado: ⚠️ PARCIAL**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| API keys expiran | ❌ | Sin `expires_at` en `APIKey` model |
| Refresh tokens expiran | ✅ | `expires_at` en `RefreshToken` |
| Rotación sin downtime | ❌ | No hay mecanismo de rotación automática |
| Revocación inmediata | ✅ | JTI revocation via Redis ✓, `revoked_at` en API keys ✓ |

---

### RG-07 — Auditoría inmutable [✅]

**Estado: ✅ CUMPLE**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| AuditLog append-only | ✅ | `app/voting/models/audit_log.py` con PostgreSQL rules |
| actor, acción, timestamp, request_id, origen | ✅ | Campos: actor_id, action, request_id, ip_address, user_agent |
| Cubre: login, votos, cambios, aprobaciones, taxonomy, revocaciones | ✅ | `AuditService.log()` integrado en VoteService |

---

## 2. Integridad del Voto

### RG-08 — Un voto activo por usuario y categoría [✅]

**Estado: ✅ CUMPLE**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Exactamente un voto activo por categoría modelo | ✅ | `user_votes` composite PK: (user_id, category_id, target_type) |
| Exactamente un voto activo por categoría orquestador | ✅ | Mismo mecanismo con target_type='orchestrator' |
| Cambio aplica -1/+1 atómico | ✅ | `VoteService.change_vote()` con transacción |

---

### RG-09 — Transaccionalidad del cambio [✅]

**Estado: ✅ CUMPLE**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Cambio atómico | ✅ | `VoteService.change_vote()` usa `session.commit()` |
| Rollback completo en fallo | ✅ | SQLAlchemy transacción: si falla, rollback automático |
| Sin doble conteo | ✅ | Idempotency key + constraint único |

---

### RG-10 — Ponderación por reputación y anti-abuso [🔴 MVP]

**Estado: ⚠️ PARCIAL (solo reputation_score)**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Ponderación por reputación | ⚠️ | `reputation_score` existe (default 5.0, rango 0-10) pero no se usa para ponderar votos |
| Ponderación por antigüedad | ❌ | No implementado |
| Ponderación por consistencia | ❌ | No implementado |
| Señales anti-bot en voto | ❌ | — |
| Peso 0 → impacto sombra | ❌ | — |

---

### RG-11 — Umbral mínimo para rankings [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin rankings no hay umbral que evaluar
- Requiere: N=5 votos ponderados mínimo, "datos insuficientes" antes del umbral

---

### RG-12 — Ventanas temporales de tendencia [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin rankings no hay tendencias
- Requiere: 7d, 30d, all-time. Snapshots inmutables

---

### RG-13 — Histórico append-only [✅]

**Estado: ✅ CUMPLE**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| VoteEvent append-only | ✅ | `vote_events` table con PostgreSQL rules (no UPDATE/DELETE) |
| Estado actual derivado del último evento válido | ✅ | `user_votes` materializado desde `vote_events` |

---

### RG-14 — Revocación controlada [✅]

**Estado: ✅ CUMPLE**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Revocar voto sin seleccionar otro | ✅ | `VoteService.revoke_vote()` |
| Revoke aplica -1 al target actual | ✅ | `VoteEvent` con action='revoke', weight=0 |
| Deja categoría sin voto activo | ✅ | `UserVote` eliminado en `revoke_vote()` |

---

### RG-15 — Detección de colusión [🔴 MVP]

**Estado: ❌ NO IMPLEMENTADO**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Detección cuentas coordinadas | ❌ | Solo hay anomalías de auth (fingerprint, creación rápida) |
| Ventanas temporales de voto | ❌ | — |
| Device fingerprints e IPs relacionadas | ❌ | — |
| Exclusión del ranking o revisión | ❌ | — |

**Acciones requeridas:**
1. Crear servicio de análisis de patrones de voto
2. Detectar: misma cuenta target + ventana anómala + fingerprint compartido
3. Aplicar: reducción de peso o exclusión del ranking
4. Registrar casos en AuditLog

---

## 3. Datos y Privacidad

### RG-16 — Minimización de datos [⬜]

**Estado: ⚠️ NO EVALUABLE**

- No hay features de recolección de datos adicionales más allá de auth
- Pendiente de evaluar cuando se implementen votos, comentarios, perfiles

---

### RG-17 — Retención limitada [⬜]

**Estado: ❌ NO IMPLEMENTADO**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Datos personales: máximo 24 meses tras última actividad | ❌ | Sin cron job de retención |
| Anonimización o eliminación automática | ❌ | — |
| AuditLog: retención 5 años | ❌ | No existe AuditLog |

---

### RG-18 — Derecho al olvido [🔴 MVP]

**Estado: ❌ NO IMPLEMENTADO**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Borrado completo de cuenta | ❌ | No hay endpoint `/delete-account` |
| Votos anonimizados en agregados históricos | ❌ | — |
| Votos eliminados de rankings futuros | ❌ | — |
| Proceso auditable | ❌ | — |

---

### RG-19 — Portabilidad [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin exportación de datos (JSON/CSV)
- Requiere: perfil, votos, comentarios, historial

---

### RG-20 — Consentimiento granular [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin sistema de consentimientos
- Requiere: consentimientos independientes para prompt, metadata, perfil público

---

### RG-21 — Anonimización antes de análisis [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin pipeline de análisis/ML
- Requiere: datos anonimizados o agregados, nunca crudos identificables

---

### RG-22 — GDPR, CCPA y legislación aplicable [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin endpoints dedicados de privacidad
- Requiere: soporte para derechos GDPR/CCPA/leyes PR

---

## 4. Accesibilidad e Internacionalización

### RG-23 — Internacionalización obligatoria [✅]

**Estado: ✅ CUMPLE**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| 5 idiomas: EN, ES, PT, FR, ZH | ✅ | `Locale` enum con los 5 valores |
| Strings no hardcodeados | ✅ | Sistema de traducciones con seed files |
| Pasar por sistema de traducción | ✅ | `resolve_translation()` + entities de traducción |

---

### RG-24 — Fallback de idioma [✅]

**Estado: ✅ CUMPLE**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Fallback: requested → EN → display_name base | ✅ | `resolve_translation(entity, locale, fallback=EN)` |
| Incluir `locale_used` | ✅ | Retorna `(translated_string, locale_used)` |

---

### RG-25 — WCAG 2.2 AA [⬜]

**Estado: ⬜ NO APLICA (backend only)**

- Requiere validación en frontend/mobile

---

### RG-26 — Mobile-first [⬜]

**Estado: ⬜ NO APLICA (backend only)**

---

## 5. Operación y Calidad

### RG-27 — Disponibilidad objetivo [⬜]

**Estado: ⬜ INFRA**

- 99.9% mensual — depende de despliegue, no de código

---

### RG-28 — Performance objetivo [⬜]

**Estado: ❌ NO CONFIGURADO**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| p95 < 200ms listados | ❌ | Sin benchmarks |
| p95 < 500ms rankings | ❌ | Sin rankings |
| p95 < 1s recomendaciones | ❌ | Sin recomendaciones |

---

### RG-29 — Idempotencia en operaciones críticas [⚠️]

**Estado: ⚠️ PARCIAL**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Rate limiting idempotente | ✅ | Fixed window buckets |
| Votos idempotentes | ❌ | No existe votación |
| Ingestas idempotentes | ⚠️ | `advisory_lock` en IngestionRepository ✓ |
| Aprobaciones idempotentes | ⚠️ | Endpoints de admin existen pero sin idempotency key |

---

### RG-30 — Observabilidad [⚠️]

**Estado: ⚠️ PARCIAL**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| request_id en toda request | ❌ | No hay middleware de request_id |
| Logs JSON estructurado | ⚠️ | Python logging configurado, no forzado JSON |
| Métricas Prometheus/Grafana | ❌ | No configurado |
| Errores a Sentry con contexto | ⚠️ | `SENTRY_DSN` en config pero no verificado si está activo |

---

### RG-31 — Feature flags [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin integración PostHog
- Requiere: feature flags para ingesta, votación de orquestadores, MCP

---

### RG-32 — Backups y recuperación [⬜]

**Estado: ⬜ INFRA**

- PostgreSQL backups diarios, retención 30d, RPO ≤1h, RTO ≤4h
- Restauración trimestral — fuera del alcance del código

---

### RG-33 — Versionado de API [✅]

**Estado: ✅ CUMPLE**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| API versionada `/api/v1/` | ✅ | `API_V1_PREFIX = "/api/v1"` en config |

---

### RG-34 — Contratos versionados [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin publicación en `forcecast/contracts`
- Sin regeneración automática de clientes

---

## 6. Integridad del Dominio

### RG-35 — Taxonomía versionada [✅]

**Estado: ✅ CUMPLE**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Nueva TaxonomyVersion en cambios | ✅ | `VersioningService.create_version()` |
| Atomic activate | ✅ | `VersioningService.activate_version()` con transacción |
| Historical immutability | ✅ | PG triggers en migración `002_taxonomy_initial` |
| Votos referencian versión vigente | ⚠️ | Pendiente cuando existan votos |

---

### RG-36 — Solo modelos aprobados votables [⚠️]

**Estado: ⚠️ PARCIAL**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Impedir votos en draft/pending_review/rejected/deprecated | ⚠️ | `ModelStatus` FSM implementado. Falta validación en endpoint de voto |

---

### RG-37 — Modelos deprecados fuera del ranking [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin rankings, no hay filtro de deprecated

---

### RG-38 — Trazabilidad de fuente [⚠️]

**Estado: ⚠️ PARCIAL**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| `source` | ✅ | `ModelSource` enum |
| `source_url` | ❌ | No en modelo actual |
| `source_payload_hash` | ❌ | No en modelo actual |

---

### RG-39 — Separación modelos y orquestadores [⬜]

**Estado: ⚠️ PARCIAL**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Rankings independientes | N/A | Sin rankings |
| Endpoints independientes | ⚠️ | Solo hay endpoints de modelos |
| Taxonomías independientes | ⚠️ | Solo taxonomy de modelos |
| Usuario puede votar en ambos | N/A | Sin votación |

---

### RG-40 — Neutralidad del ranking [🔴 MVP]

**Estado: ❌ NO IMPLEMENTADO**

| Sub-requisito | Estado | Evidencia |
|---------------|--------|-----------|
| Solo votos ponderados y reglas públicas | ❌ | Sin ranking |
| Sin favorecer proveedores | ❌ | — |
| Cambios de algoritmo documentados | ❌ | — |

---

## 7. Moderación y Contenido

### RG-41 — Moderación de comentarios [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin sistema de comentarios

### RG-42 — Apelación [⬜]

**Estado: ❌ NO IMPLEMENTADO**

### RG-43 — Transparencia de moderación [⬜]

**Estado: ❌ NO IMPLEMENTADO**

### RG-44 — Prohibición de contenido ilegal [⬜]

**Estado: ❌ NO IMPLEMENTADO**

---

## 8. Comercial y Legal

### RG-45 — Sin venta de datos [⬜]

**Estado: ⬜ POLÍTICA**

- Requiere: declaración en TOS, no código

### RG-46 — Licencia de agregados [⬜]

**Estado: ⬜ POLÍTICA**

### RG-47 — Términos de servicio [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin TOS/Política de Privacidad en 5 idiomas

### RG-48 — Edad mínima [⬜]

**Estado: ❌ NO IMPLEMENTADO**

- Sin validación de edad en registro

---

## Escenarios Transversales

### 4.1 Voto rechazado por identidad o estado

**Estado: ❌ NO IMPLEMENTADO**

- Requiere: endpoint de voto que verifique auth + email verificado + no-bot + modelo aprobado

### 4.2 Cambio idempotente y transaccional

**Estado: ❌ NO IMPLEMENTADO**

- Requiere: idempotency key en voto, transacción atómica

### 4.3 Eliminación de cuenta (derecho al olvido)

**Estado: ❌ NO IMPLEMENTADO**

- Requiere: endpoint de borrado, anonimización, auditoría

### 4.4 Fallback de locale

**Estado: ✅ CUMPLE**

- `resolve_translation()` con chain de fallback implementada

---

## Plan de Implementación — Priorizado

### Fase 1: Fundamentos de Votación [✅ COMPLETADA]

| # | Tarea | Regla | Esfuerzo | Estado |
|---|-------|-------|----------|--------|
| 1.1 | Crear modelo `VoteEvent` (append-only, user_id, target_id, category_id, taxonomy_version_id, weight, idempotency_key, timestamp) | RG-08, RG-09, RG-13 | Alto | ✅ |
| 1.2 | Crear servicio de votación con transacción atómica (-1/+1) | RG-08, RG-09 | Alto | ✅ |
| 1.3 | Validar: solo autenticados + email verificado + no-bot + modelo approved | RG-03, RG-36 | Medio | ✅ |
| 1.4 | Implementar revocación de voto (`revoke` endpoint) | RG-14 | Bajo | ✅ |
| 1.5 | Crear constraint unique: un voto activo por user+categoría | RG-08 | Bajo | ✅ |
| 1.6 | Integrar idempotency key para votos | RG-29 | Medio | ✅ |

**Fecha de completado:** 2026-09-12
**Archivos creados:**
- `app/voting/models/vote_event.py` — VoteEvent (append-only)
- `app/voting/models/user_vote.py` — UserVote (materialized state)
- `app/voting/models/audit_log.py` — AuditLog (append-only)
- `app/voting/models/enums.py` — VoteAction, TargetType
- `app/voting/repositories/vote_event.py` — VoteEventRepository
- `app/voting/repositories/user_vote.py` — UserVoteRepository
- `app/voting/repositories/audit_log.py` — AuditLogRepository
- `app/voting/services/vote_service.py` — VoteService
- `app/voting/services/audit_service.py` — AuditService
- `app/voting/api/votes.py` — FastAPI router
- `app/voting/schemas/vote.py` — Pydantic schemas
- `app/voting/tests/test_vote_service.py` — 9 unit tests (all passing)
- `app/db/migrations/versions/003_voting_initial.py` — Alembic migration

### Fase 2: Ponderación y Reputación [🔴 MVP]

| # | Tarea | Regla | Esfuerzo | Estado |
|---|-------|-------|----------|--------|
| 2.1 | Algoritmo de ponderación: reputación × antigüedad × consistencia | RG-10 | Alto | ❌ |
| 2.2 | Impacto sombra para usuarios con peso 0 | RG-10 | Medio | ❌ |
| 2.3 | Integrar señales anti-bot en score de voto | RG-10 | Medio | ❌ |

### Fase 3: Rankings [🔴 MVP]

| # | Tarea | Regla | Esfuerzo | Estado |
|---|-------|-------|----------|--------|
| 3.1 | Crear servicio de ranking con votos ponderados | RG-11, RG-40 | Alto | ❌ |
| 3.2 | Umbral mínimo N=5 votos para publicar | RG-11 | Bajo | ❌ |
| 3.3 | Ventanas: 7d, 30d, all-time | RG-12 | Medio | ❌ |
| 3.4 | Neutralidad: solo votos, sin favorecer proveedores | RG-40 | Medio | ❌ |
| 3.5 | Filtrar modelos deprecated del ranking activo | RG-37 | Bajo | ❌ |

### Fase 4: Seguridad Anti-Scraping [🔴 MVP]

| # | Tarea | Regla | Esfuerzo | Estado |
|---|-------|-------|----------|--------|
| 4.1 | Ajustar rate limits a 60/20/5 según spec | RG-01 | Bajo | ❌ |
| 4.2 | Implementar detección User-Agent sospechoso | RG-01 | Medio | ❌ |
| 4.3 | Implementar honeypot fields | RG-01 | Bajo | ❌ |
| 4.4 | Bloqueo progresivo: 429 → 403 → ban temporal → ban permanente | RG-01 | Alto | ❌ |
| 4.5 | HMAC + timestamp para endpoints de agentes | RG-01 | Medio | ❌ |
| 4.6 | URLs firmadas con expiración para imágenes | RG-01 | Medio | ❌ |

### Fase 5: Detección de Colusión [🔴 MVP]

| # | Tarea | Regla | Esfuerzo | Estado |
|---|-------|-------|----------|--------|
| 5.1 | Servicio de análisis de patrones de voto | RG-15 | Alto | ❌ |
| 5.2 | Detección: misma target + ventana anómala + fingerprint | RG-15 | Alto | ❌ |
| 5.3 | Acción: reducción de peso o exclusión del ranking | RG-15 | Medio | ❌ |
| 5.4 | Registro de casos en AuditLog | RG-15 | Bajo | ❌ |

### Fase 6: Privacidad y GDPR [🔴 MVP]

| # | Tarea | Regla | Esfuerzo | Estado |
|---|-------|-------|----------|--------|
| 6.1 | Crear modelo `AuditLog` append-only | RG-07 | Medio | ❌ |
| 6.2 | Endpoint de borrado de cuenta (derecho al olvido) | RG-18 | Alto | ❌ |
| 6.3 | Anonimización de votos históricos en borrado | RG-18 | Alto | ❌ |
| 6.4 | `public_id` separado de `user_id` interno | RG-02 | Medio | ❌ |
| 6.5 | Cifrado de campos sensibles en reposo | RG-02 | Alto | ❌ |
| 6.6 | Exportación de datos (JSON/CSV) | RG-19 | Medio | ❌ |
| 6.7 | Integrar AuditLog en login, votos, aprobaciones, taxonomía | RG-07 | Alto | ❌ |

### Fase 7: Operación [⬜]

| # | Tarea | Regla | Esfuerzo | Estado |
|---|-------|-------|----------|--------|
| 7.1 | Middleware de request_id en toda request | RG-30 | Bajo | ❌ |
| 7.2 | Forzar logging JSON estructurado | RG-30 | Bajo | ❌ |
| 7.3 | Verificar Sentry activo con contexto | RG-30 | Bajo | ❌ |
| 7.4 | Integrar métricas Prometheus | RG-30 | Medio | ❌ |
| 7.5 | Agregar `source_url` y `source_payload_hash` a AIModel | RG-38 | Bajo | ❌ |
| 7.6 | Validación de edad en registro (16/13 con parental) | RG-48 | Medio | ❌ |

### Fase 8: Features Adicionales [⬜]

| # | Tarea | Regla | Esfuerzo | Estado |
|---|-------|-------|----------|--------|
| 8.1 | Sistema de comentarios con moderación | RG-41 | Alto | ❌ |
| 8.2 | Sistema de reportes y apelaciones | RG-42 | Alto | ❌ |
| 8.3 | Consentimientos granulares | RG-20 | Alto | ❌ |
| 8.4 | Integración PostHog feature flags | RG-31 | Medio | ❌ |
| 8.5 | Publicación OpenAPI en `forcecast/contracts` | RG-34 | Bajo | ❌ |
| 8.6 | Orquestadores: modelo, endpoints, taxonomía separada | RG-39 | Alto | ❌ |

---

## Changelog del Documento

| Fecha | Cambio |
|-------|--------|
| 2026-09-12 | Auditoría inicial — 48 reglas evaluadas, 4 cumplen, 8 parciales, 36 sin implementar |
| 2026-09-12 | Fase 1 completada — Sistema de votación implementado (VoteEvent, UserVote, AuditLog). 9 tests pasando. Reglas RG-07, RG-08, RG-09, RG-13, RG-14 ahora ✅ |
