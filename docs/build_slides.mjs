import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const root = path.resolve(import.meta.dirname, "..");
const skill = "C:/Users/USER/.codex/plugins/cache/openai-primary-runtime/presentations/26.1118.11504/skills/presentations";
const runtimePython = "C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1118-904-0_26.1118.904.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe";
process.env.RUNTIME_NODE_MODULES = "C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1118-904-0_26.1118.904.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules";
const build = path.join(root, ".build", "slides");
const output = path.join(root, "entregables", "presentacion_final.pptx");
await fs.mkdir(build, { recursive: true });
await fs.mkdir(path.dirname(output), { recursive: true });

const data = JSON.parse(await fs.readFile(path.join(root, "output", "analysis.json"), "utf8"));
const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const NAVY = "#142941", TEAL = "#087D81", LIGHT = "#EAF2F4", GRAY = "#526372";

function txt(slide, value, x, y, w, h, size = 24, bold = false, color = NAVY) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none", line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = value;
  shape.text.style = { fontFamily: "Arial", fontSize: `${size}pt`, bold, color };
  return shape;
}
function slide(title, n) {
  const s = presentation.slides.add();
  s.background.fill = "#FFFFFF";
  txt(s, title, 72, 48, 1136, 90, 39, true);
  txt(s, `${n} / 9`, 1080, 659, 130, 32, 20, false, GRAY);
  return s;
}
function bar(s, y) {
  s.shapes.add({ geometry: "rect", position: { left: 72, top: y, width: 1136, height: 4 }, fill: TEAL, line: { style: "solid", fill: "none", width: 0 } });
}

{
  const s = presentation.slides.add();
  s.background.fill = NAVY;
  txt(s, "Monitoreo de movilidad\nurbana", 80, 130, 1020, 200, 48, true, "#FFFFFF");
  txt(s, "Yellow Taxi 2023 · Datos masivos", 80, 360, 1050, 80, 28, false, "#CDE5E5");
  txt(s, "David Fernando Parra Pardo", 80, 565, 800, 60, 24, false, "#FFFFFF");
}
{
  const s = slide("Problema y datos", 2);
  txt(s, "¿Cuándo y entre qué zonas se concentran los viajes y los trayectos lentos?", 80, 160, 1060, 100, 30, true);
  bar(s, 290);
  txt(s, "530.000", 80, 330, 300, 75, 42, true, TEAL);
  txt(s, "filas originales", 80, 408, 320, 42, 23);
  txt(s, "509.885", 470, 330, 320, 75, 42, true, TEAL);
  txt(s, "viajes válidos", 470, 408, 340, 42, 23);
  txt(s, "Muestra inicial de enero de 2023 · Fuente: NYC Open Data / TLC", 80, 535, 1060, 80, 22, false, GRAY);
}
{
  const s = slide("Arquitectura de extremo a extremo", 3);
  const lanes = [
    ["Operación", "CSV  →  Kafka  →  Spark  →  Cassandra"],
    ["Grafo", "CSV  →  NetworkX  →  Neo4j"],
    ["Histórico", "CSV  →  Parquet  →  S3  →  Snowflake"],
  ];
  lanes.forEach(([label, chain], i) => {
    const y = 176 + i * 138;
    txt(s, label, 80, y, 210, 55, 24, true, TEAL);
    txt(s, chain, 288, y - 7, 890, 85, 26, true);
    if (i < 2) bar(s, y + 89);
  });
  txt(s, "Local verificado: Kafka · Spark · Cassandra · Neo4j     |     Nube: scripts preparados", 80, 608, 1070, 45, 20, false, GRAY);
}
{
  const s = slide("Decisión de diseño", 4);
  txt(s, "Tres modelos según la consulta", 80, 168, 1010, 65, 32, true, TEAL);
  txt(s, "Cassandra: ruta + tiempo\nNeo4j: conexiones entre zonas\nSnowflake: agregaciones históricas", 80, 260, 1060, 220, 26);
  bar(s, 505);
  txt(s, "Alternativa descartada: un único almacén para todos los accesos.", 80, 535, 1080, 90, 24, true);
}
{
  const s = slide("Modelado de datos", 5);
  txt(s, "Grafo", 80, 170, 250, 50, 30, true, TEAL);
  txt(s, "Zone(id, PageRank, intermediación)\nROUTE(origen → destino, viajes, tiempo medio)", 80, 225, 1050, 140, 25);
  bar(s, 380);
  txt(s, "Cassandra", 80, 412, 300, 50, 30, true, TEAL);
  txt(s, "trip_events: ruta · bucket de 15 min · shard\nroute_windows: ruta · día · ventana de 5 min", 80, 468, 1090, 130, 25);
}
{
  const s = slide("Cinco análisis reproducibles", 6);
  const a = data.analyses;
  const rows = [
    `Hora pico: ${a.peak_hours[0].hour}:00 → ${a.peak_hours[0].trips.toLocaleString("es-CO")} viajes`,
    `Origen principal: zona ${a.top_origins[0].zone} → ${a.top_origins[0].trips.toLocaleString("es-CO")}`,
    `Destino principal: zona ${a.top_destinations[0].zone} → ${a.top_destinations[0].trips.toLocaleString("es-CO")}`,
    `Ruta más frecuente: ${a.top_routes[0].route_id} → ${a.top_routes[0].trips.toLocaleString("es-CO")}`,
    `Ruta lenta (≥30 viajes): ${a.slow_routes_min_30[0].route_id} → ${(a.slow_routes_min_30[0].slow_share*100).toFixed(1)} %`,
  ];
  rows.forEach((row, i) => txt(s, row, 80, 170 + i * 88, 1070, 65, 25, i === 0));
}
{
  const s = slide("Hallazgos del grafo", 7);
  txt(s, "259 zonas", 80, 175, 500, 85, 40, true, TEAL);
  txt(s, "11.934 rutas", 610, 175, 600, 85, 36, true, TEAL);
  bar(s, 300);
  txt(s, "Zona 236: mayor PageRank (0,03009)\nZona 132: mayor intermediación (0,08248)", 80, 340, 1080, 150, 27);
  txt(s, "Una relación representa viajes observados; no una calle directa.", 80, 550, 1080, 70, 22, false, GRAY);
}
{
  const s = slide("Escala y demostración", 8);
  txt(s, "509.885 viajes válidos", 80, 170, 1070, 75, 40, true, TEAL);
  txt(s, `Cinco análisis locales: ${data.elapsed_seconds.toFixed(3)} s`, 80, 275, 1070, 70, 31, true);
  bar(s, 385);
  txt(s, "Demo: 1.000 eventos → Kafka → Spark → Cassandra\nConsulta CQL y ranking Cypher visibles", 80, 430, 1080, 155, 25);
}
{
  const s = slide("Límites y próximos pasos", 9);
  txt(s, "Muestra de pocos días · Sin GPS · Flujo histórico reproducido", 80, 170, 1100, 110, 27, true);
  txt(s, "S3 y Snowflake: scripts sin ejecución verificada en nube", 80, 300, 1080, 65, 25);
  txt(s, "Licencia del conjunto no especificada: verificar su reutilización", 80, 370, 1080, 65, 22);
  bar(s, 450);
  txt(s, "Ampliar meses, medir latencia y costos, deduplicar micro lotes", 80, 495, 1080, 100, 26, true, TEAL);
}

for (const [i, s] of presentation.slides.items.entries()) {
  const blob = await presentation.export({ slide: s, format: "png", scale: 1 });
  await fs.writeFile(path.join(build, `slide-${String(i+1).padStart(2,"0")}.png`), new Uint8Array(await blob.arrayBuffer()));
}
const { finalizePresentation } = await import(pathToFileURL(path.join(skill, "container_tools", "artifact_tool_utils.mjs")).href);
const candidatePath = path.join(build, "candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const result = await finalizePresentation({
  explicitTotalSlideCount: 9,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  workspaceDir: root,
  candidatePath,
  finalPath: output,
  pythonExecutable: runtimePython,
  integrityValidatorPath: path.join(skill, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skill, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit"],
  fontPolicy: { basis: "design", families: ["Arial"] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(build, "validation-final.json"),
});
console.log(JSON.stringify({ output, result }, null, 2));
