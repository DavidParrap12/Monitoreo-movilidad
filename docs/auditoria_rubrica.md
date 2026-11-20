# Auditoría de entregables

Fecha de revisión: 19 de noviembre de 2026. Estados: C cumple, P parcial, N no cumple o falta evidencia. La evaluación final corresponde al docente.

| Criterio | Estado | Evidencia y acción pendiente |
|---|---|---|
| A. Problema | C | Problema y cinco preguntas en README e informe; la velocidad es reproducción histórica. |
| B. Datos | P | 530.000 filas, 509.885 válidas, descargador reproducible y limpieza documentada. La ficha oficial no especifica licencia; confirmar permiso antes de redistribución pública. |
| C. Arquitectura | P | Kafka, Spark, Cassandra y Neo4j locales; S3 y Snowflake tienen scripts, pero su ejecución no se ha verificado con cuentas de nube. |
| D. Modelado | P | Grafo de zonas y rutas y dos tablas Cassandra por patrón de consulta. La tabla histórica Snowflake está definida, pero faltan particionado de archivos y validación con carga real. |
| E. Implementación | P | Cinco análisis locales medidos; falta validar la ruta en nube y una corrida completa de 509.885 eventos por streaming. |
| F. Informe | C | PDF de 10 páginas dentro del ZIP con resultados locales, limitaciones, trabajo individual y bibliografía. |
| G. Presentación | P | Presentación PDF y guion de 10 minutos; el documento de entrega incluye un enlace de video, pero la exposición y las preguntas se evalúan en vivo. |
| H. Equipo y entrega | P | Un integrante; historial Git muestra un autor. Hay un documento con enlace de video; faltan la autoevaluación individual y la entrega en la plataforma antes del plazo. |

## Riesgos prioritarios

1. **Licencia:** NYC Open Data marca la licencia del conjunto como no especificada. En una entrega privada al curso se debe conservar la atribución y verificar las condiciones de distribución antes de publicar el CSV.
2. **Credenciales y nube:** `.env` está ignorado; `.env.example` contiene solo un valor de ejemplo. Configurar AWS y Snowflake en el entorno sin añadir secretos al repositorio. No atribuir resultados locales a Snowflake.
3. **Demostración:** la ruta de 1.000 eventos debe ensayarse con servicios activos y checkpoints conocidos. Kafka y Spark pueden conservar estado entre ensayos.
4. **Evidencia personal:** el video y la autoevaluación deben reflejar el trabajo real de David Fernando Parra Pardo. No se pueden generar de manera honesta a partir del código.

## Referencias

- NYC Open Data, [2023 Yellow Taxi Trip Data](https://data.cityofnewyork.us/Transportation/2023-Yellow-Taxi-Trip-Data/4b4i-vvec).
- NYC Taxi and Limousine Commission, [TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).
