# Monitoreo de movilidad urbana (NYC Taxi)

Prototipo con viajes Yellow Taxi de 2023. Cada viaje es un evento entre zonas TLC. El CSV **no contiene GPS, identificador de taxi ni sensores en tiempo real**: el productor reproduce viajes históricos en Kafka y `route_id = origen:destino` sustituye a un identificador de sensor. Se excluyen registros con fecha fuera de 2023, los IDs TLC 264 (desconocido) y 265 (fuera de NYC), duraciones fuera de 1 minuto a 4 horas, distancias fuera de 0 a 200 km y velocidades mayores de 130 km/h. `slow_share` (viajes bajo 15 km/h) es un indicador aproximado, no una medición directa de congestión vial.

## Arquitectura

`CSV -> productor Python -> Kafka -> Spark Structured Streaming -> Cassandra`

`CSV -> NetworkX -> CSV de resultados / Neo4j`

`CSV -> Parquet -> S3 -> Snowflake`

Se requieren Python 3.11, Docker Desktop con motor Linux y, para la ruta histórica en nube, cuentas AWS y Snowflake. El CSV `nyc_taxi_500k.csv` incluye **530.000 filas originales y 509.885 viajes válidos** (SHA-256: `3ecdc14a2f51b68127135ab62bf740925a72526074e2b42251e2c7ec3efc5ceb`). La muestra ordenada por ID proviene del conjunto [2023 Yellow Taxi Trip Data](https://data.cityofnewyork.us/Transportation/2023-Yellow-Taxi-Trip-Data/4b4i-vvec) de NYC Open Data, provisto por TLC. La ficha oficial indica **licencia no especificada**; debe verificarse el permiso de reutilización antes de redistribuir públicamente los datos. La muestra representa una parte inicial del conjunto, no todo 2023.

## Problema y preguntas

El prototipo busca identificar patrones de demanda y viajes lentos entre zonas de taxi a partir de viajes históricos. Responde qué horas concentran más viajes, qué zonas originan y reciben más viajes, cuáles rutas tienen más volumen, cuáles presentan mayor proporción de viajes bajo 15 km/h y qué zonas son más centrales en el grafo. El volumen y la variedad de consultas justifican separar eventos operativos, relaciones entre zonas y análisis histórico; la velocidad aquí es **simulada por reproducción**, no telemetría real.

## Flujo local

En PowerShell, desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edite .env y cambie NEO4J_PASSWORD por una contraseña local propia.
docker compose up -d kafka cassandra neo4j
```

Si aparece `ModuleNotFoundError`, instale y ejecute con el mismo intérprete sin depender de la activación de PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m mobility.graph --origin 161 --destination 237
```

Arranque Spark. Compose esperará a que Cassandra responda, creará `mobility` y sus tablas mediante `cassandra-init`, y después iniciará el procesamiento:

```powershell
docker compose --profile stream up -d spark
python -m mobility.producer --input nyc_taxi_500k.csv --limit 10000
```

Compruebe los resultados:

```powershell
docker compose logs -f spark
docker compose exec cassandra cqlsh -e "SELECT * FROM mobility.route_windows LIMIT 5;"
```

El productor acepta `--rate 100` para dosificar, `--skip 400000` para omitir viajes válidos anteriores y `--limit 0` (por defecto) para publicar todo. Publique después de que Spark esté activo. El primer inicio de Spark descarga los conectores Maven. Ambos flujos tienen checkpoints separados bajo `checkpoints/<tema>/`. Las claves de Cassandra son estables ante reintentos de micro lotes; publicar el mismo CSV otra vez sí puede duplicar conteos de ventanas si los eventos aún no son tardíos según el watermark. Para otra corrida de desarrollo, defina un `KAFKA_TOPIC` nuevo antes de levantar Spark y publique con `--topic` del mismo valor; vea el paso a paso de la demo.

## Diseño de Cassandra

`trip_events`: clave de partición `(route_id, bucket_start, shard)`, con buckets de 15 minutos y ocho shards. Acota el crecimiento de cada partición en rutas activas; `event_time, trip_id` ordenan e identifican eventos. Una consulta por ruta y hora cubre cuatro buckets y ocho shards por bucket. Con telemetría real, use `vehicle_id` o `sensor_id` en la clave si necesita series por vehículo.

`route_windows`: clave de partición `(route_id, event_date)` con máximo de 288 ventanas de cinco minutos por día y ruta. El watermark es de 30 minutos: eventos posteriores pueden descartarse de la agregación aunque persistan en `trip_events`. Spark interpreta las marcas locales del CSV en `America/New_York`.

## Grafo

```powershell
python -m mobility.graph --origin 161 --destination 237
```

El comando muestra el avance cada 100.000 viajes válidos y anuncia el cálculo de centralidad. `Ctrl+C` lo interrumpe; vuelva a ejecutarlo para obtener los CSV completos.

Los nodos son zonas TLC y las aristas dirigidas son viajes observados. `trips` pondera PageRank; `mean_minutes` pondera intermediación y la ruta de menor tiempo medio. Los resultados quedan en `output/graph/zones.csv` y `routes.csv`.

Para explorar **todas las zonas y rutas en un HTML local** (resumen, rankings, filtros y caminos de menor tiempo medio), genere el panel a partir de esos CSV y ábralo en el navegador:

```powershell
.\.venv\Scripts\python.exe -m mobility.dashboard
Start-Process .\output\graph\index.html
```

El archivo funciona sin servidor ni conexión a Neo4j. Es una instantánea: vuelva a ejecutar `mobility.graph` y después `mobility.dashboard` cuando cambien los datos.

La carga opcional reemplaza los nodos `Zone` existentes en Neo4j. Para cargar el grafo, establezca `NEO4J_PASSWORD` en la sesión de PowerShell con el mismo valor guardado en `.env`:

```powershell
$env:NEO4J_PASSWORD = ((Get-Content .env | Where-Object { $_ -match '^NEO4J_PASSWORD=' } | Select-Object -First 1) -replace '^NEO4J_PASSWORD=', '')
python -m mobility.graph --load-neo4j
```

Abra `http://localhost:7474` con el usuario `neo4j` y esa contraseña:

```cypher
MATCH (z:Zone) RETURN z.id, z.pagerank, z.betweenness ORDER BY z.pagerank DESC LIMIT 10;
```

Zonas sin viajes en el archivo no aparecen. Una arista de viaje observado no demuestra conectividad vial directa; la ruta calculada es una secuencia de zonas según tiempos medios de viaje.

## Histórico en S3 y Snowflake

```powershell
python -m mobility.export_history
python -m mobility.export_history --s3-bucket MI_BUCKET --s3-key mobility/nyc-taxi-2023/trips.parquet
```

La subida usa la cadena de credenciales estándar de boto3. En [snowflake/analysis.sql](snowflake/analysis.sql), reemplace `YOUR_BUCKET` y `YOUR_S3_INTEGRATION` por un bucket y una integración de almacenamiento con acceso de lectura. Ejecute el SQL con un rol autorizado. Incluye `COPY INTO` y consultas de horas pico, rutas lentas y zonas activas. Para recargas, use una clave S3 nueva o gestione explícitamente el historial de carga de Snowflake.

## Reproducción de datos y resultados

```powershell
python archivos.py --rows 530000
python -m mobility.analyze
python -m mobility.graph --origin 161 --destination 237
python -m mobility.export_history
```

`archivos.py` descarga páginas de 25.000 filas con orden estable `:id`, valida cada página y reemplaza el CSV solo después de terminar. La API puede corregir registros históricos; por eso se publica el SHA-256 de la muestra usada para el informe. `mobility.analyze` genera cinco análisis, conteos y tiempo local en `output/analysis.json`. Las cifras del informe se derivan de ese archivo y del grafo, no de consultas ejecutadas en Snowflake. Para la demostración cronometrada y el video de respaldo, vea [docs/demo.md](docs/demo.md).

## Entregables del curso

- [ZIP de entrega](entregables.zip): informe técnico de 10 páginas, presentación PDF de nueve diapositivas y documento con el enlace del video. La carpeta `entregables/` se excluye de Git.
- [Paso a paso de comandos para la demo y el video](docs/demo.md).
- [Auditoría de la rúbrica](docs/auditoria_rubrica.md) y [plantilla de autoevaluación confidencial](docs/plantilla_autoevaluacion.md).

La autoevaluación completada se adjunta por separado en la plataforma del curso. No guarde la autoevaluación personal ni credenciales en un repositorio público. `docs/build_report.py` puede generar una versión técnica de ocho páginas desde `output/analysis.json` para reproducir las métricas; el PDF final del curso está dentro del ZIP.

## Integrante

David Fernando Parra Pardo: ingesta, limpieza, procesamiento, modelado, análisis, documentación y demostración. El historial Git registra actualmente commits bajo el nombre abreviado David Parra Pardo; configure el nombre completo en Git para los próximos commits si así lo requiere el docente.

## Comprobación

```powershell
python -m unittest discover -s tests -v
docker compose config
```

El entorno Compose tiene un broker, un nodo Cassandra y un Neo4j para demostración. Producción requeriría réplicas, autenticación, gestión de secretos, observabilidad y retención.
