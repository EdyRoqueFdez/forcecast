# Investigación y dirección de producto

**Fecha de corte:** 2026-09-11  
**Mercado objetivo:** Global  
**Perfil del fundador:** Una persona apoyada por herramientas de IA  
**Estrategia:** MVP pequeño -> validación con usuarios -> contenido/comunidad -> monetización y expansión

> Este documento conserva el contexto de investigación y las decisiones tomadas antes de iniciar un proyecto limpio. Las cifras de ingresos deben tratarse como escenarios, no como previsiones garantizadas.

## 1. Objetivo

Identificar hasta tres oportunidades de apps con competencia relativa baja o con una diferenciación alcanzable, que puedan ser construidas y operadas inicialmente por una sola persona.

La oportunidad no se debe evaluar únicamente por el tamaño del mercado. Debe cumplir la mayor parte de estos criterios:

- Resuelve un problema frecuente y suficientemente doloroso.
- Tiene una disposición de pago clara.
- Puede tener un MVP funcional en aproximadamente 2-6 semanas.
- Puede conseguir usuarios mediante contenido, SEO, comunidades o distribución orgánica.
- No depende desde el primer día de grandes volúmenes de datos propietarios.
- No requiere soporte 24/7, moderación intensa o acuerdos empresariales.
- Puede empezar con una versión gratuita o de bajo coste y monetizar después.
- Tiene una posible ventaja defendible: datos, workflow, comunidad, reputación o integración.

## 2. Contexto del fundador

La prioridad es lanzar un MVP, observar la aceptación de la comunidad y producir contenido nuevo según las señales de uso. El producto inicial debe poder mantenerse con recursos limitados.

Decisiones actuales:

- Mercado: global.
- Idioma inicial recomendado: inglés.
- Español: posible expansión posterior si se detecta tracción o menor competencia.
- Recursos: una persona con ayuda de IA.
- Modelo de negocio: equilibrio entre ingresos tempranos y un activo defendible.
- Distribución: contenido demostrable, SEO, comunidades y recomendaciones orgánicas antes de depender de anuncios.

## 3. Advertencia sobre competencia

“Poca competencia” no significa ausencia total de competidores. Toda categoría atractiva tendrá sustitutos, hojas de cálculo, comunidades, herramientas generalistas o competidores indirectos.

La evaluación correcta es:

1. Qué productos resuelven hoy el mismo problema.
2. Qué parte de la experiencia dejan sin resolver.
3. Qué usuarios están desatendidos.
4. Qué ventaja concreta puede construir una persona en un nicho específico.
5. Si esa ventaja puede probarse antes de invertir meses en desarrollo.

## 4. Criterios de puntuación recomendados

Cada idea debe recibir una puntuación de 1 a 5 en cada criterio:

| Criterio | Pregunta |
|---|---|
| Dolor | ¿El problema cuesta tiempo, dinero o frustración real? |
| Frecuencia | ¿El usuario lo encuentra semanalmente o diariamente? |
| Pago | ¿Existe una razón clara para pagar? |
| Competencia relativa | ¿Hay un hueco concreto aunque existan alternativas? |
| MVP | ¿Una persona puede lanzarlo en 2-6 semanas? |
| Distribución | ¿Puede crecer mediante contenido o comunidad? |
| Retención | ¿El usuario tiene motivos para volver? |
| Defensibilidad | ¿La ventaja mejora con datos, comunidad o workflow? |
| Riesgo operativo | ¿Puede operar sin moderación o soporte constante? |
| Riesgo legal | ¿Evita problemas regulatorios importantes? |

La recomendación final debe mostrar la puntuación y explicar los sacrificios. No se debe escoger una idea únicamente porque tenga un mercado grande.

## 5. Estado del repositorio Forcecast

El repositorio existente está en `backend/` y contiene un esqueleto de FastAPI con SQLAlchemy async, configuración, health checks y una especificación de dominio para una plataforma de opiniones y selección de modelos de IA.

### Implementado antes de este documento

- Aplicación FastAPI.
- Configuración con Pydantic Settings.
- Motor SQLAlchemy async para PostgreSQL.
- Health checks en `/health` y `/api/v1/health`.
- Dependencias declaradas para FastAPI, PostgreSQL, Redis, JWT, HTTPX, pytest, Ruff y mypy.

### No implementado inicialmente

- Modelos de dominio reales.
- Autenticación.
- Votaciones.
- Comparaciones persistidas.
- Recomendaciones.
- Ingestión desde proveedores externos.
- API pública de catálogo.
- Panel administrativo.
- Frontend.
- Datos reales persistidos.

### Especificación existente

La especificación de taxonomía describe:

- Proveedores de IA.
- Modelos y versiones.
- Modalidades: texto, visión, audio, código y razonamiento.
- Ventana de contexto.
- Precio de referencia por millón de tokens.
- Categorías como coding, debugging, architecture y documentation.
- Traducciones.
- Versionado de taxonomía.
- Ingestión desde OpenRouter, Hugging Face y LMSYS.
- Aprobación manual de modelos.
- API pública y API administrativa.
- Webhooks de ciclo de vida.

La especificación aclara que Forcecast es una plataforma de comparación/votación, no un marketplace. Los precios son información de referencia, no cobros ni precios de venta.

## 6. Hipótesis de producto Forcecast

Forcecast puede evolucionar hacia una herramienta para responder:

> “¿Qué modelo de IA debería usar para esta tarea concreta, considerando calidad, modalidad, contexto y coste?”

La propuesta de valor inicial podría ser un catálogo comparativo orientado a tareas, no un simple directorio de modelos.

Ejemplos de tareas:

- Programar.
- Depurar código.
- Diseñar arquitectura.
- Documentar.
- Razonar sobre problemas complejos.
- Analizar imágenes.
- Trabajar con contextos extensos.

La diferenciación posible:

- Comparación por caso de uso, no solo por benchmarks.
- Opiniones de usuarios con contexto de la tarea.
- Coste de referencia visible junto con la utilidad.
- Filtros por modalidad, capacidad y ventana de contexto.
- Votaciones y recomendaciones explicables.
- Datos estructurados que puedan convertirse después en API o integración para desarrolladores.

### Riesgo de esta idea

El catálogo de modelos cambia rápidamente. Los precios, nombres, capacidades y disponibilidad deben actualizarse. Además, existen directorios y comparadores generalistas, por lo que la ventaja debe estar en el contexto de uso, la calidad de las opiniones y la experiencia de decisión.

No se debe construir una plataforma grande antes de demostrar que los usuarios vuelven para decidir entre modelos.

## 7. Primer vertical técnico que se empezó a implementar

Antes de pausar, se creó una primera versión mínima en el backend:

- Esquemas Pydantic para modelos de catálogo.
- Catálogo en memoria con cinco modelos de ejemplo.
- Búsqueda por nombre, slug o proveedor.
- Filtro por categoría.
- Filtro por modalidad.
- Filtro por proveedor.
- Paginación simple por `limit` y `offset`.
- Comparación de modelos mediante slugs.
- Lista de slugs no encontrados.
- Router público bajo `/api/v1/catalog`.
- Interruptor `DATABASE_ENABLED`, desactivado por defecto para poder probar este MVP sin PostgreSQL.

Endpoints del primer vertical:

```text
GET /api/v1/catalog/models
GET /api/v1/catalog/models/compare?slugs=gpt-4.1&slugs=deepseek-r1
```

Este vertical es una prueba de contrato y de caso de uso, no todavía una implementación definitiva. El catálogo debe migrarse a base de datos cuando se valide que existe demanda.

## 8. Entidades previstas para el producto completo

### Provider

- Identificador.
- Slug.
- Nombre.
- Sitio web.
- Documentación.
- Estado.

### AIModel

- Identificador.
- Slug.
- Nombre visible.
- Versión.
- Familia.
- Modalidades.
- Ventana de contexto.
- Máximo de salida.
- Precio de entrada de referencia.
- Precio de salida de referencia.
- Fecha de lanzamiento.
- Estado de aprobación.
- Fuente y URL.
- Hash del payload de origen para deduplicación.

### Category

- Slug.
- Nombre traducido.
- Descripción.
- Versión de taxonomía.
- Categoría padre opcional.

### ModelCategory

Relación entre modelos y tareas/capacidades.

### ModelHosting

Proveedor o endpoint donde se ofrece un modelo. No debe incluir overrides de precio en la versión inicial.

### Opinion o Vote, fase posterior

- Usuario anónimo o autenticado.
- Modelo.
- Categoría/tarea.
- Contexto de uso.
- Voto o puntuación.
- Comentario opcional.
- Fecha.
- Señales de confianza y moderación.

### Comparison

- Modelos seleccionados.
- Tarea o categoría.
- Criterios comparados.
- Resultado visible.
- Fecha de generación.

## 9. Lógica de negocio prevista

### Descubrimiento

1. El usuario entra al catálogo.
2. Selecciona una tarea o escribe una búsqueda.
3. El sistema normaliza la consulta.
4. Se filtran modelos aprobados por categoría, modalidad, proveedor y disponibilidad de datos.
5. Se devuelve una lista paginada.
6. Cada modelo muestra capacidades, precio de referencia y fuente.

### Comparación

1. El usuario selecciona entre dos y cuatro modelos.
2. El sistema valida que existan.
3. Se cargan sus datos normalizados.
4. Se muestran lado a lado.
5. Los campos ausentes se representan como “sin datos”, nunca como cero.
6. La comparación puede incluir opiniones agregadas por tarea cuando exista suficiente volumen.

### Opiniones y votaciones, fase posterior

1. El usuario elige modelo y tarea.
2. Indica resultado de su experiencia.
3. Puede añadir contexto, coste aproximado y comentario.
4. El sistema aplica límites anti-spam.
5. El comentario entra en moderación si contiene señales de riesgo.
6. Se recalcula la puntuación agregada.
7. Se muestra volumen de votos y fecha de actualización.

### Ingestión

1. Se ejecuta una importación manual desde una fuente.
2. Se valida el payload.
3. Se normalizan slugs y nombres.
4. Se calcula hash del origen.
5. Se hace upsert por claves de proveedor/modelo.
6. Los nuevos modelos quedan pendientes de revisión.
7. Se registra el resultado y los errores.
8. Solo los aprobados aparecen públicamente.

## 10. Monetización posible

### Fase gratuita

- Catálogo público.
- Comparaciones básicas.
- Votos y opiniones limitados.
- Contenido SEO.

### Fase Pro individual

Posibles beneficios:

- Comparaciones guardadas.
- Historial de decisiones.
- Filtros avanzados.
- Alertas de cambios de precio o disponibilidad.
- Exportación.
- Espacios de trabajo personales.

Rango inicial que debe validarse con entrevistas: aproximadamente 5-15 USD mensuales.

### Fase desarrolladores/equipos

- API con límite de uso.
- Feed de cambios.
- Integración con herramientas internas.
- Historial y snapshots.
- Uso comercial.

Esta fase puede tener precios superiores, pero no debe construirse antes de validar el uso individual.

### Afiliación

Se puede estudiar afiliación hacia proveedores de modelos, siempre separando claramente contenido editorial, votos de usuarios y enlaces comerciales. No debe influir en las puntuaciones.

## 11. Métricas de validación

Antes de ampliar el producto:

- Visitantes que llegan desde contenido.
- Porcentaje que realiza una búsqueda.
- Porcentaje que compara al menos dos modelos.
- Comparaciones por usuario.
- Usuarios que regresan en 7 y 30 días.
- Suscripciones a una lista de espera.
- Clics en alertas o fuentes.
- Votos y opiniones cualificadas.
- Conversión a plan de pago.

Señal mínima razonable para continuar tras un experimento:

- Usuarios reales usando la comparación sin que el fundador los guíe.
- Repetición del uso para tareas distintas.
- Comentarios que pidan una función concreta.
- Primeras personas dispuestas a pagar o dejar datos de contacto para pagar después.

## 12. Experimento recomendado de 14-30 días

### Semana 1: problema y audiencia

- Elegir un nicho inicial: desarrolladores que comparan modelos para programar y depurar.
- Publicar páginas o posts comparando modelos para tareas concretas.
- Entrevistar o conversar con usuarios de comunidades relevantes.
- Registrar preguntas repetidas y modelos que realmente comparan.

### Semana 2: prototipo

- Lanzar catálogo mínimo.
- Incorporar cinco a diez modelos.
- Crear comparaciones orientadas a tareas.
- Añadir formulario de feedback y lista de espera.

### Semanas 3-4: distribución y decisión

- Publicar resultados y comparaciones actualizadas.
- Medir búsquedas, comparaciones, retornos y solicitudes.
- Preguntar por alertas, historial y API.
- Decidir continuar, cambiar de nicho o descartar.

## 13. Investigación de mercado pendiente

En la sesión inicial se intentó consultar informes recientes de mercado y suscripciones, pero varias páginas externas no devolvieron contenido extraíble de forma fiable en el entorno. Por ese motivo, no se deben presentar como hechos confirmados cifras actuales de cuota, crecimiento o ingresos de terceros sin volver a verificarlas.

Antes de decidir las tres apps definitivas hay que completar:

- Revisión de al menos cinco competidores o sustitutos por idea.
- Precios públicos actuales.
- Reseñas negativas recientes.
- Señales de demanda en comunidades y búsquedas.
- Coste de adquisición orgánica y de pago cuando sea estimable.
- Retención observable o proxies razonables.
- Restricciones regulatorias.

## 14. Plantilla para proyecciones de ingresos

Cada idea debe calcularse con tres escenarios:

```text
MRR bruto = usuarios activos de pago x precio mensual medio
MRR neto aproximado = MRR bruto - comisión de pagos - infraestructura - herramientas - marketing
```

También se debe incluir:

- Usuarios activos mensuales.
- Conversión gratuita a pago.
- Precio medio.
- Churn mensual.
- Comisión de App Store, Google Play o procesador web.
- Coste de infraestructura.
- Coste de APIs de IA.
- Coste de contenido y distribución.
- Sensibilidad con conversión a la mitad.
- Sensibilidad con churn duplicado.

No se debe llamar “beneficio” al ingreso bruto.

## 15. Orden recomendado de construcción

1. Validar un único usuario inicial y una tarea concreta.
2. Publicar catálogo mínimo y comparador.
3. Medir uso real.
4. Añadir fuentes y actualización de datos.
5. Añadir cuentas y comparaciones guardadas.
6. Añadir votaciones y reputación.
7. Añadir recomendaciones explicables.
8. Añadir API o funcionalidades para equipos.

## 16. Principios para el proyecto limpio

- Leer este archivo antes de diseñar la arquitectura.
- No implementar todo el dominio de la especificación desde el día uno.
- Separar catálogo, opiniones, recomendaciones y monetización.
- Mantener los precios como información de referencia.
- No inventar benchmarks ni puntuaciones.
- Mostrar la fecha y fuente de cualquier dato externo.
- Diseñar los contratos HTTP antes de conectar persistencia.
- Probar primero el flujo principal de descubrimiento y comparación.
- Añadir persistencia solo cuando el MVP tenga señales de uso.
- Mantener una ruta clara para reemplazar datos en memoria por SQLAlchemy.

## 17. Próxima instrucción para iniciar el proyecto limpio

Al comenzar el nuevo proyecto, leer este documento y decidir explícitamente:

1. Qué de las tres oportunidades se va a construir primero.
2. Quién es el usuario inicial.
3. Qué problema exacto se valida.
4. Qué entra y qué queda fuera del MVP.
5. Qué métrica determina continuar o descartar.
6. Qué stack y despliegue se utilizarán.
7. Qué datos son reales, cuáles son semilla y cuáles necesitan fuente.

La primera versión debe poder demostrarse de extremo a extremo antes de construir autenticación, pagos, ingestión automática o un sistema complejo de recomendaciones.
