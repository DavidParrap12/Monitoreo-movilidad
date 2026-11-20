"""Build the eight-page technical report from measured local outputs."""

import csv
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "entregables" / "informe_tecnico.pdf"
DATA = json.loads((ROOT / "output" / "analysis.json").read_text(encoding="utf-8"))
W, H = A4
NAVY = colors.HexColor("#142941")
TEAL = colors.HexColor("#087D81")
GRAY = colors.HexColor("#4D5A67")
LIGHT = colors.HexColor("#EAF2F4")
M = 48

pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))

styles = {
    "body": ParagraphStyle("body", fontName="Arial", fontSize=10.5, leading=15, textColor=NAVY, alignment=TA_LEFT),
    "small": ParagraphStyle("small", fontName="Arial", fontSize=9.2, leading=12.5, textColor=NAVY),
    "head": ParagraphStyle("head", fontName="Arial-Bold", fontSize=12, leading=16, textColor=TEAL),
    "cell": ParagraphStyle("cell", fontName="Arial", fontSize=9.2, leading=12.5, textColor=NAVY),
    "cellbold": ParagraphStyle("cellbold", fontName="Arial-Bold", fontSize=9.2, leading=12.5, textColor=NAVY),
}


class Page:
    def __init__(self, pdf, number, title):
        self.pdf = pdf
        self.number = number
        self.y = H - 54
        pdf.setFillColor(TEAL)
        pdf.rect(M, H - 42, 35, 4, fill=1, stroke=0)
        pdf.setFont("Arial-Bold", 19)
        pdf.setFillColor(NAVY)
        pdf.drawString(M, self.y, title)
        self.y -= 22
        pdf.setStrokeColor(colors.HexColor("#D4E1E6"))
        pdf.line(M, self.y, W - M, self.y)
        self.y -= 20

    def para(self, text, kind="body", gap=8):
        p = Paragraph(text, styles[kind])
        width, height = p.wrap(W - 2 * M, 999)
        self.y -= height
        p.drawOn(self.pdf, M, self.y)
        self.y -= gap
        self.check()

    def head(self, text):
        self.y -= 5
        self.para(text, "head", 6)

    def table(self, rows, widths, gap=12):
        formatted = []
        for index, row in enumerate(rows):
            formatted.append([Paragraph(str(cell), styles["cellbold" if index == 0 else "cell"]) for cell in row])
        table = Table(formatted, colWidths=widths, hAlign="LEFT", repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, TEAL),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FBFC")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
        ]))
        _, height = table.wrap(W - 2 * M, 999)
        self.y -= height
        table.drawOn(self.pdf, M, self.y)
        self.y -= gap
        self.check()

    def check(self):
        if self.y < 65:
            raise ValueError(f"Page {self.number} overflows: y={self.y:.1f}")

    def finish(self):
        self.pdf.setStrokeColor(colors.HexColor("#D4E1E6"))
        self.pdf.line(M, 46, W - M, 46)
        self.pdf.setFont("Arial", 8)
        self.pdf.setFillColor(GRAY)
        self.pdf.drawString(M, 34, "Monitoreo de movilidad urbana | David Fernando Parra Pardo")
        self.pdf.drawRightString(W - M, 34, f"{self.number} / 8")
        self.pdf.showPage()


def fmt(n):
    return f"{n:,}".replace(",", ".")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(OUT), pagesize=A4)
    pdf.setTitle("Informe técnico - Monitoreo de movilidad urbana")
    a = DATA["analyses"]

    p = Page(pdf, 1, "Monitoreo de movilidad urbana")
    p.y -= 16
    p.para("<b>Yellow Taxi 2023 | informe técnico</b>", "head", 14)
    p.para("Prototipo de datos masivos para analizar viajes entre zonas de taxi de Nueva York. Reproduce eventos históricos por Kafka, agrega ventanas con Spark, consulta series en Cassandra y representa zonas conectadas en Neo4j. Exporta el histórico a Parquet para una ruta opcional S3 / Snowflake.", gap=22)
    p.table([
        ["Datos originales", "Viajes válidos", "Zonas del grafo", "Rutas del grafo"],
        [fmt(DATA["raw_records"]), fmt(DATA["valid_records"]), "259", fmt(DATA["distinct_routes"])],
    ], [125, 125, 125, 125], gap=23)
    p.head("Alcance de la evidencia")
    p.para("Se verificaron la ingesta local, los cinco análisis reproducibles, la exportación Parquet, la carga del grafo en Neo4j y una publicación de 1.000 eventos con salida visible en Cassandra. Los scripts S3 y Snowflake están preparados, pero no se atribuyen resultados a servicios de nube no ejecutados.")
    p.head("Autor y fecha")
    p.para("David Fernando Parra Pardo. Trabajo individual. Revisión: 19 de noviembre de 2026.")
    p.finish()

    p = Page(pdf, 2, "1. Problema y datos")
    p.head("Pregunta principal")
    p.para("¿Dónde y cuándo se concentra la actividad de taxi, y qué conexiones entre zonas presentan una mayor proporción de viajes lentos? Las preguntas operativas requieren consultar eventos por ruta y tiempo; las preguntas relacionales requieren navegar un grafo; las históricas agregan cientos de miles de filas.")
    p.head("Fuente, muestra y licencia")
    p.para("NYC Open Data, conjunto <i>2023 Yellow Taxi Trip Data</i> (TLC, ID 4b4i-vvec). Se tomaron las primeras 530.000 filas ordenadas por ID mediante API paginada. La ficha del conjunto indica licencia no especificada. La muestra no representa todo el año: sus viajes válidos corresponden a los primeros días de enero de 2023. No debe generalizarse a todo NYC ni a todo 2023.")
    p.table([
        ["Campo de entrada", "Uso"],
        ["tpep_pickup_datetime / tpep_dropoff_datetime", "Marca temporal y duración"],
        ["PULocationID / DOLocationID", "Origen, destino y ruta dirigida"],
        ["trip_distance", "Distancia y velocidad aproximada"],
    ], [250, 250])
    p.head("Limpieza")
    p.para(f"Se conservan {fmt(DATA['valid_records'])} de {fmt(DATA['raw_records'])} filas ({DATA['valid_share']*100:.1f} %). Se excluyen fechas fuera de 2023, zonas 264 y 265, duraciones fuera de 1 minuto a 4 horas, distancias de 0 a 200 km y velocidades mayores de 130 km/h. Se crea un ID estable por fila y ruta origen:destino. Los campos monetarios no se usan.")
    p.para("El CSV no incluye GPS continuo, identificador de vehículo ni sensores. La velocidad proviene de distancia / duración del viaje; la fracción bajo 15 km/h es solo un indicador aproximado de lentitud.", "small")
    p.finish()

    p = Page(pdf, 3, "2. Arquitectura e integración")
    p.para("La misma fuente alimenta tres rutas para patrones de consulta distintos. Kafka, Spark, Cassandra y Neo4j se ejecutan localmente con Docker Compose; S3 y Snowflake requieren configuración de cuentas aparte.")
    p.head("Flujo de extremo a extremo")
    for label, target in [
        ("Operativa", "CSV  →  Kafka  →  Spark  →  Cassandra"),
        ("Relacional", "CSV  →  NetworkX  →  Neo4j"),
        ("Histórica", "CSV  →  Parquet  →  S3  →  Snowflake"),
    ]:
        p.pdf.setFillColor(LIGHT)
        p.pdf.roundRect(M, p.y - 25, W - 2 * M, 29, 5, fill=1, stroke=0)
        p.pdf.setFont("Arial-Bold", 9)
        p.pdf.setFillColor(TEAL)
        p.pdf.drawString(M + 9, p.y - 15, label)
        p.pdf.setFont("Arial", 10)
        p.pdf.setFillColor(NAVY)
        p.pdf.drawString(M + 92, p.y - 15, target)
        p.y -= 36
    p.y -= 6
    p.table([
        ["Ruta", "Flujo de datos", "Consulta prevista"],
        ["Operativa", "CSV → productor Python → Kafka → Spark Structured Streaming → Cassandra", "Eventos por ruta y tiempo; ventanas de cinco minutos"],
        ["Relacional", "CSV → NetworkX → Neo4j", "Centralidad y conexiones entre zonas"],
        ["Histórica", "CSV → Parquet → S3 → Snowflake", "Agregaciones SQL y comparación temporal"],
    ], [85, 270, 145], gap=18)
    p.head("Integración comprobada")
    p.para("En la ejecución local se publicaron 1.000 eventos en Kafka. Spark mantuvo dos consultas de streaming y la tabla Cassandra <i>route_windows</i> devolvió filas con ruta, fecha, inicio de ventana y conteo. Neo4j recibió 259 nodos Zone y 11.934 relaciones ROUTE. La carga histórica exportó 509.885 eventos válidos a Parquet.")
    p.head("Secuencia de demostración")
    p.para("Los datos grandes se precargan. En vivo se muestran servicios activos, un micro lote de 1.000 viajes, una consulta CQL con resultado visible y una consulta Cypher sobre el grafo. El guion reserva cuatro minutos para esta secuencia dentro de los diez minutos de exposición.")
    p.head("Límites de la arquitectura")
    p.para("El productor reproduce marcas históricas; no hay latencia de sensores reales. Los tres ramales comparten el CSV pero la rama de Neo4j no se actualiza automáticamente con cada micro lote. S3 y Snowflake son rutas implementadas en scripts, sin verificación de ejecución en nube.")
    p.finish()

    p = Page(pdf, 4, "3. Decisiones tecnológicas")
    p.table([
        ["Tecnología elegida", "Motivo técnico", "Alternativa / compromiso"],
        ["Kafka", "Desacopla productor y proceso; permite reproducción controlada.", "Archivo directo: más simple, sin flujo observable."],
        ["Spark Structured Streaming", "Ventanas de cinco minutos con watermark y escritura por micro lote.", "Python puro: menos operación, menos adecuado para crecer."],
        ["Cassandra", "Particiones por ruta y tiempo para lectura operativa.", "SQL único: más flexible, menos especializado para escrituras por serie."],
        ["Neo4j + NetworkX", "Relaciones dirigidas entre zonas y consultas Cypher; cálculo de centralidad local.", "Tablas de adyacencia: menos natural para recorridos."],
        ["Parquet + S3 + Snowflake", "Archivo columnar y consultas históricas separadas de la operación.", "Todo en Cassandra: agregaciones globales costosas."],
    ], [105, 200, 195], gap=18)
    p.head("Decisión principal")
    p.para("Se separaron la tabla operativa, el grafo y el histórico. Un único almacén simplificaría el despliegue, pero mezclaría accesos por ruta y tiempo, recorridos de relaciones y agregaciones globales. El costo de esta elección es duplicación de datos y mayor complejidad de sincronización.")
    p.head("Compromisos")
    p.para("El despliegue local usa un broker Kafka, un nodo Cassandra y un Neo4j: sirve para una demostración, no ofrece alta disponibilidad. El watermark de 30 minutos puede descartar eventos tardíos de las ventanas. En nube habría costos de almacenamiento, consultas y transferencia, aún no medidos.")
    p.finish()

    p = Page(pdf, 5, "4. Modelado de datos")
    p.head("Grafo de zonas")
    p.para("Nodo <b>Zone</b>: id de zona TLC, PageRank e intermediación. Relación dirigida <b>ROUTE</b>: origen→destino, número de viajes y duración media en minutos. La ruta calculada entre zonas usa tiempos medios de viajes observados; no describe necesariamente calles conectadas.")
    p.head("Cassandra: tablas derivadas de consultas")
    p.table([
        ["Tabla", "Clave", "Patrón de consulta"],
        ["trip_events", "Partición (route_id, bucket_start, shard); clustering event_time DESC, trip_id", "Eventos recientes de una ruta en buckets de 15 minutos; ocho shards reducen particiones calientes."],
        ["route_windows", "Partición (route_id, event_date); clustering window_start DESC", "Ventanas de cinco minutos de una ruta en un día; máximo 288 ventanas por partición."],
    ], [95, 215, 190], gap=16)
    p.head("Histórico analítico")
    p.para("El archivo Parquet zstd contiene ocho campos canónicos: trip_id, route_id, origin_zone, destination_zone, event_time, duration_s, distance_km y speed_kmh. En S3 se propone <i>mobility/nyc-taxi-2023/trips.parquet</i>. La tabla Snowflake TRIPS conserva esos campos; un stage externo y COPY INTO materializan las filas para SQL. Una carga productiva debería particionar archivos por fecha para recargas y poda de lectura.")
    p.finish()

    p = Page(pdf, 6, "5. Resultados e interpretación")
    peak = a["peak_hours"][0]
    origin = a["top_origins"][0]
    dest = a["top_destinations"][0]
    top = a["top_routes"][0]
    slow = a["slow_routes_min_30"][0]
    p.table([
        ["Análisis reproducible", "Salida local", "Interpretación"],
        ["1. Hora de salida más frecuente", f"{peak['hour']}:00: {fmt(peak['trips'])} viajes", "La muestra concentra más salidas a esa hora; no implica patrón anual."],
        ["2. Origen con más salidas", f"Zona {origin['zone']}: {fmt(origin['trips'])}", "Alta actividad de origen dentro de la muestra."],
        ["3. Destino con más llegadas", f"Zona {dest['zone']}: {fmt(dest['trips'])}", "El destino principal difiere del origen principal."],
        ["4. Ruta con más viajes", f"{top['route_id']}: {fmt(top['trips'])}; {top['mean_minutes']} min", "La demanda es dirigida; el sentido inverso tiene otro volumen."],
        ["5. Ruta con mayor fracción lenta (≥30 viajes)", f"{slow['route_id']}: {fmt(slow['trips'])}; {slow['slow_share']*100:.1f} %", "Señal de viajes lentos según velocidad calculada, no congestión vial medida."],
    ], [160, 140, 200], gap=20)
    p.head("Grafo y consulta en vivo")
    p.para("El grafo contiene 259 zonas y 11.934 rutas dirigidas. La zona 236 lidera PageRank ponderado por viajes (0,03009). La zona 132 presenta la mayor intermediación ponderada por duración (0,08248). Neo4j permite mostrar el ranking con Cypher; Cassandra permite inspeccionar ventanas por ruta y fecha.")
    p.head("Reproducción")
    p.para("Ejecute <i>python -m mobility.analyze</i> para regenerar output/analysis.json. Los cinco resultados anteriores provienen de ese archivo. El ranking del grafo proviene de <i>python -m mobility.graph</i> y de output/graph/zones.csv.")
    p.head("Cinco horas con más salidas en la muestra")
    maximum = a["peak_hours"][0]["trips"]
    for row in a["peak_hours"]:
        p.pdf.setFont("Arial", 9)
        p.pdf.setFillColor(NAVY)
        p.pdf.drawString(M, p.y - 11, f"{row['hour']}:00")
        p.pdf.setFillColor(TEAL)
        p.pdf.roundRect(M + 53, p.y - 13, 310 * row["trips"] / maximum, 13, 3, fill=1, stroke=0)
        p.pdf.setFillColor(NAVY)
        p.pdf.drawRightString(W - M, p.y - 11, fmt(row["trips"]))
        p.y -= 24
    p.y -= 6
    p.check()
    p.finish()

    p = Page(pdf, 7, "6. Rendimiento y escala")
    p.head("Medición local")
    p.table([
        ["Medida", "Resultado", "Alcance"],
        ["Filas CSV / válidas", f"{fmt(DATA['raw_records'])} / {fmt(DATA['valid_records'])}", "Se supera el mínimo de 500.000 después de limpiar."],
        ["Tiempo de cinco análisis", f"{DATA['elapsed_seconds']:.3f} s", "Una ejecución local Python; incluye hash, conteo y agregaciones."],
        ["Rutas distintas", fmt(DATA["distinct_routes"]), "Pares origen-destino observados."],
        ["Tamaño CSV / Parquet", "60,6 MB / 16,6 MB", "Parquet conserva ocho campos; no es una comparación de compresión pura."],
        ["Prueba de flujo", "1.000 eventos publicados", "Kafka → Spark → Cassandra; filas CQL visibles."],
    ], [145, 140, 215], gap=17)
    p.head("Cuellos de botella")
    p.para("El análisis local relee el CSV completo y calcula hash antes de agregar; la lectura y el parseo por fila dominan esta ruta. El cálculo de intermediación del grafo crece con el número de zonas y relaciones. El arranque de Spark depende de conectores Maven y tarda más en frío. No se midió un benchmark de latencia Kafka→Cassandra ni una prueba con volúmenes crecientes.")
    p.head("Interpretación de la prueba")
    p.para("La evidencia demuestra escala de entrada y funcionamiento del micro lote. No prueba rendimiento de producción: los contenedores son de un nodo, los checkpoints pueden conservar estado previo y no se registró una comparación controlada entre configuraciones.")
    p.finish()

    p = Page(pdf, 8, "7. Limitaciones y cierre")
    p.head("Limitaciones y riesgos")
    p.para("La muestra cubre sobre todo los primeros días de enero; no representa la estacionalidad de 2023. No hay GPS ni datos de tráfico en tiempo real. La licencia de la ficha oficial es no especificada, por lo que se debe confirmar la reutilización antes de publicar el CSV. La repetición del CSV en Kafka duplica conteos de ventanas. Cassandra local no ofrece réplicas. AWS y Snowflake implican costos no medidos y credenciales externas.")
    p.head("Trabajo futuro")
    p.para("Ampliar a meses completos y particionar Parquet por fecha. Añadir IDs de evento y deduplicación de streaming, pruebas con volúmenes crecientes, observabilidad de latencia y costos de nube. Sincronizar el grafo incrementalmente si se requiere que refleje el flujo en tiempo real.")
    p.head("Distribución del trabajo")
    p.para("Trabajo individual de David Fernando Parra Pardo: fuente y descarga, limpieza, productor Kafka, procesamiento Spark, esquemas Cassandra y Snowflake, análisis de grafo, pruebas locales, informe y presentación. La autoevaluación individual y la grabación de la demo se entregan por separado.")
    p.head("Bibliografía")
    p.para("NYC Open Data. <i>2023 Yellow Taxi Trip Data</i>. https://data.cityofnewyork.us/Transportation/2023-Yellow-Taxi-Trip-Data/4b4i-vvec", "small")
    p.para("NYC Taxi and Limousine Commission. <i>TLC Trip Record Data</i>. https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page", "small")
    p.para("Código y evidencias del proyecto: README.md, mobility/analyze.py, output/analysis.json, output/graph/zones.csv, cassandra/schema.cql y snowflake/analysis.sql.", "small")
    p.finish()

    pdf.save()
    print(OUT)


if __name__ == "__main__":
    main()
