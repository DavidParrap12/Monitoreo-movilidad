# Paso a paso para la presentación y el video

Este guion está pensado para **PowerShell en Windows**, desde la carpeta del proyecto. En el video debes salir en cámara y mostrar tu pantalla al mismo tiempo. Deja la cámara en una esquina que no tape los resultados de la terminal. La grabación de respaldo dura **3 a 5 minutos**; la exposición en vivo dura **10 minutos** y luego hay **5 minutos de preguntas**.

## 1. Preparar todo antes de grabar

Abre PowerShell y entra al proyecto:

```powershell
cd 'C:\Users\USER\Documents\Monitoreo-movilidad'
python --version
docker --version
```

La primera vez, instala las dependencias y crea tu archivo local de contraseña:

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

En Notepad cambia `replace-with-your-local-password` por una contraseña propia de **al menos ocho caracteres** y guarda. **Haz esto antes de iniciar la grabación** para que la contraseña no aparezca en pantalla. Si `.env` ya existe y funciona, no lo sobrescribas. Si cambias la contraseña después de crear el volumen de Neo4j, cambiar `.env` por sí solo no cambia la contraseña guardada en la base. Para que el script de Neo4j use la misma contraseña, ejecuta en la misma terminal:

```powershell
$env:NEO4J_PASSWORD = ((Get-Content .env | Where-Object { $_ -match '^NEO4J_PASSWORD=' } | Select-Object -First 1) -replace '^NEO4J_PASSWORD=', '')
```

Levanta los servicios:

```powershell
docker compose up -d kafka cassandra neo4j
docker compose ps
```

Para que el video tenga un flujo nuevo y sus propios checkpoints, prepara un tema Kafka con nombre único. Conserva esta misma terminal abierta hasta terminar el video:

```powershell
$env:KAFKA_TOPIC = 'demo-' + (Get-Date -Format 'yyyyMMddHHmmss')
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh --create --if-not-exists --bootstrap-server kafka:19092 --topic $env:KAFKA_TOPIC --partitions 1 --replication-factor 1
docker compose --profile stream up -d --force-recreate spark
```

Espera a que `kafka`, `cassandra`, `neo4j` y `spark` aparezcan como **Up**. Además, espera a que Spark termine de descargar conectores y empiece las consultas; puede tardar más de un minuto. Usa `docker compose logs --tail 25 spark` para comprobarlo. Si acabas de crear `.env` sobre un volumen antiguo de Neo4j, la contraseña anterior puede seguir activa; no borres el volumen para arreglarlo, usa la contraseña que ya tenía o actualízala en Neo4j.

Carga el grafo y genera la evidencia local. Hazlo **antes de grabar**, porque lee las 530.000 filas y tarda varios segundos:

```powershell
python -m mobility.graph --load-neo4j
python -m mobility.analyze
python -m mobility.export_history
```

Comprueba que aparezca `Loaded graph into Neo4j`, que el análisis indique **530000 raw_records** y **509885 valid_records**, y que Parquet exporte **509885 trips**. La fuente puede cambiar en el futuro; si el hash o los conteos difieren, usa el CSV incluido en la entrega para reproducir las cifras del informe.

Abre `http://localhost:7474` en el navegador. Inicia sesión con usuario `neo4j` y la contraseña de `.env`. **Pega la consulta siguiente en la barra de consultas de Neo4j Browser, nunca directamente en PowerShell.** Deja preparada esta consulta:

```cypher
MATCH (z:Zone)
RETURN z.id AS zona, round(z.pagerank, 5) AS pagerank
ORDER BY pagerank DESC
LIMIT 5;
```

## 2. Grabar el video: comandos en orden

Antes de comenzar, abre tu cámara y deja visibles tu rostro y PowerShell. Di en una frase: «Voy a mostrar un flujo con datos históricos de taxi: Kafka recibe, Spark procesa, Cassandra guarda ventanas y Neo4j permite consultar el grafo».

**Paso A — servicios activos.** Ejecuta:

```powershell
docker compose ps
```

Muestra las cuatro filas activas y explica que son componentes diferentes del sistema.

**Paso B — publicar datos nuevos.** Ejecuta:

```powershell
python -m mobility.producer --topic $env:KAFKA_TOPIC --skip 400000 --limit 1000
docker compose exec -T kafka /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server kafka:19092 --topic $env:KAFKA_TOPIC
```

Espera `Published 1000 events` y un offset final de `1000`. Di que son viajes históricos reproducidos, no sensores en vivo. Se omiten los primeros 400.000 viajes válidos para elegir un tramo posterior de la muestra que no estuviera cargado en ensayos cortos previos.

**Paso C — consultar Cassandra.** Ejecuta:

```powershell
docker compose exec -T cassandra cqlsh -e "SELECT route_id, event_date, window_start, trip_count FROM mobility.route_windows WHERE route_id='163:262' AND event_date='2023-01-06' LIMIT 5;"
```

Debes ver filas con `route_id`, fecha, ventana y conteo. Explica que Spark agrupa por ventanas de cinco minutos y Cassandra permite leer una ruta y un día sin recorrer toda la tabla. `cqlsh` muestra marcas en UTC; el CSV y Spark interpretan las horas originales en `America/New_York`. Si la tabla aparece vacía, espera unos segundos y repite la consulta; revisa `docker compose logs --tail 50 spark`. El primer viaje de este lote tiene ruta `163:262` y hora local `2023-01-06 01:02:19`; su ventana es `2023-01-06 06:00:00+0000` en CQL.

**Paso D — consultar Neo4j.** Cambia al navegador y ejecuta la consulta Cypher preparada. Debes ver la zona **236** entre los primeros resultados, con PageRank alrededor de **0,03009**. Di que este grafo se precargó desde el mismo CSV y que una relación representa viajes observados entre zonas.

Si prefieres mostrar el resultado **en PowerShell**, usa este comando completo en una sola línea; no pegues `MATCH`, `RETURN`, `ORDER` y `LIMIT` como comandos separados:

```powershell
docker compose exec -T neo4j cypher-shell -u neo4j -p $env:NEO4J_PASSWORD "MATCH (z:Zone) RETURN z.id AS zona, round(z.pagerank, 5) AS pagerank ORDER BY pagerank DESC LIMIT 5;"
```

**Paso E — mostrar escala.** Vuelve a PowerShell:

```powershell
Get-Content .\output\analysis.json -Raw | ConvertFrom-Json | Select-Object raw_records, valid_records, distinct_routes, elapsed_seconds
```

Explica que **509.885** viajes válidos superan el mínimo de 500.000. El tiempo puede cambiar según el equipo; muestra el valor real que salga en tu terminal. Cierra diciendo que la muestra cubre pocos días de enero y que S3/Snowflake no forman parte de esta prueba local.

## 3. Si algo falla durante la grabación

- `docker compose ps` no muestra un servicio: vuelve a ejecutar `docker compose up -d kafka cassandra neo4j` y `docker compose --profile stream up -d spark`.
- El productor no conecta a Kafka: espera a que Kafka termine de arrancar y prueba `docker compose logs --tail 30 kafka`.
- Cassandra no devuelve filas: ejecuta `docker compose logs --tail 50 spark`; asegúrate de publicar después de que Spark esté activo.
- Neo4j no arranca y el log dice `minimum password length is 8 characters`: la contraseña de `.env` es demasiado corta. Usa una de al menos ocho caracteres. Si el volumen ya tenía otra contraseña, debes cambiarla en Neo4j; `.env` no la reemplaza automáticamente.
- Neo4j rechaza el inicio de sesión: verifica que la variable `NEO4J_PASSWORD` coincide con la contraseña del volumen ya creado. La variable de Compose solo establece la contraseña inicial de un volumen nuevo.
- Una segunda grabación puede repetir los mismos eventos y aumentar los conteos de ventanas. Explica este límite o usa una toma limpia; evita afirmar que el conteo de Cassandra equivale al total de viajes únicos.

## 4. Entrega del video

Revisa el archivo completo antes de subirlo: rostro visible, voz audible, comandos legibles, resultados CQL y Cypher visibles, duración entre 3 y 5 minutos. El archivo debe ser una grabación real tuya; este documento es el guion para producirla.

## 5. Distribución de la exposición en vivo

La tabla sugerida en el enunciado suma 15 minutos, aunque el límite de exposición es 10 minutos exactos. Usa esta distribución y deja los 5 minutos de preguntas aparte.

| Minuto | Acción visible | Explicación |
|---|---|---|
| 0:00-1:30 | Diapositivas 1-2 | Problema, datos TLC y límites de la muestra. |
| 1:30-3:30 | Diapositivas 3-4 | Arquitectura y decisión de separar consultas operativas, grafo y análisis. |
| 3:30-7:30 | Terminal y Neo4j | Mostrar Kafka, Spark y Cassandra; publicar 1.000 eventos, ejecutar CQL y Cypher. |
| 7:30-9:30 | Diapositivas 5-8 | Cinco hallazgos locales, 509.885 eventos válidos y tiempo de análisis. |
| 9:30-10:00 | Diapositiva 9 | Limitaciones y cierre. |
