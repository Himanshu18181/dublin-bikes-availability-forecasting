/* Dublin Bikes CA presentation - 11 slides, dark theme matching the dashboard */
const pptxgen = require("pptxgenjs");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");

const FIG = "D:/Domain Appliucation Project/outputs/figures/";
const OUT = "D:/Domain Appliucation Project/presentation/DublinBikes_Presentation.pptx";

// palette (dashboard brand)
const BG = "0B1220", CARD = "111C2E", CARD2 = "16233B";
const BLUE = "3B82F6", DEEP = "1D4ED8", ICE = "CADCFC";
const INK = "E2E8F0", MUTED = "8B94A7", AMBER = "F59E0B", GREEN = "22C55E", RED = "EF4444";
const F = "Calibri";

async function icon(name, hex) {
  const el = React.createElement(fa[name], { color: "#" + hex, size: 256 });
  const svg = renderToStaticMarkup(el);
  const buf = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const icons = {};
  const names = ["FaBicycle","FaWarehouse","FaTruck","FaDatabase","FaCheckCircle","FaClock",
    "FaCalendarAlt","FaChartBar","FaBell","FaSlidersH","FaMapMarkedAlt","FaUsers","FaFlask",
    "FaUserShield","FaBalanceScale","FaLeaf","FaArrowRight","FaTable","FaChartLine","FaTree",
    "FaRocket","FaExclamationTriangle","FaCloudSun","FaRoute"];
  for (const n of names) icons[n] = await icon(n, "FFFFFF");
  const iconsBlue = {};
  for (const n of ["FaBicycle"]) iconsBlue[n] = await icon(n, "FFFFFF");

  const p = new pptxgen();
  p.layout = "LAYOUT_WIDE";                        // 13.33 x 7.5
  p.defineSlideMaster({ title: "DARK", background: { color: BG } });

  const W = 13.33, M = 0.65;

  // helpers ------------------------------------------------------------
  function kicker(s, txt, y = 0.55) {
    s.addText(txt.toUpperCase(), { x: M, y, w: 8, h: 0.3, fontFace: F, fontSize: 12,
      color: BLUE, bold: true, charSpacing: 3, margin: 0 });
  }
  function title(s, txt, y = 0.88, w = W - 2 * M, size = 34) {
    s.addText(txt, { x: M, y, w, h: 0.75, fontFace: F, fontSize: size, color: INK,
      bold: true, margin: 0 });
  }
  function card(s, x, y, w, h, fill = CARD) {
    s.addShape("roundRect", { x, y, w, h, fill: { color: fill }, rectRadius: 0.09,
      line: { color: "223052", width: 0.75 } });
  }
  function circleIcon(s, x, y, ic, d = 0.62, color = BLUE) {
    s.addShape("ellipse", { x, y, w: d, h: d, fill: { color } });
    const pad = d * 0.24;
    s.addImage({ data: icons[ic], x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad });
  }
  function pageno(s, n) {
    s.addText(String(n), { x: W - 0.75, y: 7.02, w: 0.4, h: 0.3, fontFace: F, fontSize: 10,
      color: MUTED, align: "right", margin: 0 });
    s.addText("Dublin Bikes · Domain Applications CA", { x: M, y: 7.02, w: 5, h: 0.3,
      fontFace: F, fontSize: 10, color: MUTED, margin: 0 });
  }
  function stat(s, x, y, w, big, label, color = ICE) {
    s.addText(big, { x, y, w, h: 0.85, fontFace: F, fontSize: 40, bold: true, color,
      align: "center", margin: 0 });
    s.addText(label, { x, y: y + 0.82, w, h: 0.55, fontFace: F, fontSize: 12.5,
      color: MUTED, align: "center", margin: 0 });
  }
  function whiteImg(s, path, x, y, w, h) {           // rounded white frame + figure
    s.addShape("roundRect", { x, y, w, h, fill: { color: "FFFFFF" }, rectRadius: 0.08,
      line: { color: "223052", width: 0.75 } });
    s.addImage({ path, x: x + 0.12, y: y + 0.12, w: w - 0.24, h: h - 0.24 });
  }

  // ================= 1 · TITLE =================
  let s = p.addSlide({ masterName: "DARK" });
  s.addShape("ellipse", { x: 8.4, y: -2.6, w: 8.5, h: 8.5, fill: { color: "0E1B33" } });
  s.addShape("ellipse", { x: 10.2, y: -1.2, w: 5.4, h: 5.4, fill: { color: "13233F" } });
  s.addShape("roundRect", { x: M, y: 1.05, w: 1.05, h: 1.05, rectRadius: 0.24,
    fill: { color: DEEP } });
  s.addImage({ data: icons.FaBicycle, x: M + 0.24, y: 1.29, w: 0.57, h: 0.57 });
  s.addText("NCI · MSC DATA ANALYTICS · DOMAIN APPLICATIONS", { x: M, y: 2.45, w: 9, h: 0.3,
    fontFace: F, fontSize: 12.5, color: BLUE, bold: true, charSpacing: 3, margin: 0 });
  s.addText("Before the Docks Run Dry", { x: M, y: 2.82, w: 11.6, h: 0.95, fontFace: F,
    fontSize: 52, bold: true, color: INK, margin: 0 });
  s.addText("Forecasting Dublin Bikes availability for proactive rebalancing\nwith open urban data",
    { x: M, y: 3.85, w: 10.5, h: 0.95, fontFace: F, fontSize: 20, color: ICE, margin: 0 });
  s.addShape("line", { x: M, y: 5.35, w: 3.2, h: 0, line: { color: "223052", width: 1 } });
  s.addText([
    { text: "Himanshu Devendrasing Rajput", options: { fontSize: 16, color: INK, bold: true, breakLine: true } },
    { text: "x24230308  ·  School of Computing  ·  National College of Ireland", options: { fontSize: 12.5, color: MUTED } },
  ], { x: M, y: 5.55, w: 9, h: 0.8, fontFace: F, margin: 0 });
  s.addNotes("Good morning. In the next four minutes: a real operational problem, an honest model, and a working tool you will see live.");

  // ================= 2 · PROBLEM =================
  s = p.addSlide({ masterName: "DARK" });
  kicker(s, "The problem");
  title(s, "A bike-share fails in two directions — and the fix is reactive");
  const rows2 = [
    ["FaBicycle", RED, "Empty station", "No bikes at 08:00 — the commuter walks. 21.5% of June station-hours were empty-risk."],
    ["FaWarehouse", AMBER, "Full station", "No free dock — the return is blocked and the rider is stranded at the wrong end."],
    ["FaTruck", BLUE, "Costly rebalancing", "Crews truck bikes between stations, usually dispatched after the failure has already happened."],
  ];
  rows2.forEach((r, i) => {
    const y = 2.0 + i * 1.5;
    card(s, M, y, 7.35, 1.28);
    circleIcon(s, M + 0.3, y + 0.33, r[0], 0.62, r[1]);
    s.addText(r[2], { x: M + 1.15, y: y + 0.16, w: 5.9, h: 0.4, fontFace: F, fontSize: 17,
      bold: true, color: INK, margin: 0 });
    s.addText(r[3], { x: M + 1.15, y: y + 0.56, w: 5.95, h: 0.62, fontFace: F, fontSize: 12.5,
      color: MUTED, margin: 0 });
  });
  card(s, 8.45, 2.0, 4.2, 4.28, CARD2);
  s.addText("THE PREMISE", { x: 8.75, y: 2.3, w: 3.6, h: 0.3, fontFace: F, fontSize: 11,
    color: BLUE, bold: true, charSpacing: 2, margin: 0 });
  s.addText("The failure is predictable.", { x: 8.75, y: 2.68, w: 3.7, h: 0.85, fontFace: F,
    fontSize: 22, bold: true, color: INK, margin: 0 });
  s.addText("If hourly availability can be forecast per station, crews can be routed before stations run dry — not after.",
    { x: 8.75, y: 3.6, w: 3.6, h: 1.4, fontFace: F, fontSize: 14, color: ICE, margin: 0 });
  s.addText("115 stations · Dublin city core", { x: 8.75, y: 5.6, w: 3.6, h: 0.35,
    fontFace: F, fontSize: 12, color: MUTED, margin: 0 });
  pageno(s, 2);
  s.addNotes("Two failure modes: empty blocks pick-ups, full blocks returns. Rebalancing is reactive and expensive. Premise: the failure is predictable, so act before it.");

  // ================= 3 · DATA =================
  s = p.addSlide({ masterName: "DARK" });
  kicker(s, "The data");
  title(s, "Real, open, current — the Smart Dublin station feed");
  stat(s, M, 2.15, 3.9, "1.86M", "raw 5-minute snapshots · Apr–Jun 2026");
  stat(s, 4.7, 2.15, 3.9, "249,940", "station-hours after aggregation");
  stat(s, 8.75, 2.15, 3.9, "115", "docking stations across the city");
  card(s, M, 4.0, 12.03, 2.35, CARD);
  s.addText("QUALITY AUDIT — THE FEED IS REMARKABLY CLEAN", { x: M + 0.35, y: 4.28, w: 11, h: 0.3,
    fontFace: F, fontSize: 11.5, color: BLUE, bold: true, charSpacing: 2, margin: 0 });
  const chips = [
    ["0", "missing values"], ["0", "duplicate snapshots"], ["0", "impossible readings"],
    ["1", "offline row dropped"], ["7.4", "snapshots / station-hour"],
  ];
  chips.forEach((c, i) => {
    const x = M + 0.35 + i * 2.33;
    s.addText(c[0], { x, y: 4.68, w: 2.1, h: 0.6, fontFace: F, fontSize: 28, bold: true,
      color: GREEN, margin: 0 });
    s.addText(c[1], { x, y: 5.3, w: 2.15, h: 0.65, fontFace: F, fontSize: 11.5, color: MUTED, margin: 0 });
  });
  s.addText("The real preprocessing contribution is reshaping, not scrubbing: irregular 5-minute snapshots → one clean hourly row per station.",
    { x: M, y: 6.55, w: 12, h: 0.4, fontFace: F, fontSize: 13, italic: true, color: ICE, margin: 0 });
  pageno(s, 3);
  s.addNotes("Fully open Dublin City Council feed, no synthetic data. 1.86 million snapshots become 249,940 station-hours. Audit: essentially zero defects — the work is reshaping, not scrubbing.");

  // ================= 4 · RHYTHM =================
  s = p.addSlide({ masterName: "DARK" });
  kicker(s, "Exploratory analysis");
  title(s, "The commuter tide is the signal");
  whiteImg(s, FIG + "eda_occupancy_heatmap.png", M, 1.95, 6.55, 4.75);
  const pts4 = [
    ["FaClock", "Weekday mornings drain the docks; evenings refill them — a sharp, repeating pulse."],
    ["FaCalendarAlt", "Weekends are flat: the pattern is commuting, not leisure."],
    ["FaChartBar", "This weekly rhythm is exactly what the models must capture — and what the naive baseline memorises."],
  ];
  pts4.forEach((r, i) => {
    const y = 2.25 + i * 1.45;
    circleIcon(s, 7.65, y, r[0], 0.56);
    s.addText(r[1], { x: 8.45, y: y - 0.08, w: 4.25, h: 1.25, fontFace: F, fontSize: 14.5,
      color: INK, margin: 0 });
  });
  pageno(s, 4);
  s.addNotes("Mean occupancy by hour and weekday. Green = bikes available. The tide: morning drain, evening refill, absent at weekends. This is the predictable structure.");

  // ================= 5 · METHOD =================
  s = p.addSlide({ masterName: "DARK" });
  kicker(s, "Method");
  title(s, "Four models, one honest test: predict a month never seen");
  // temporal split bar
  card(s, M, 2.0, 12.03, 1.5, CARD);
  s.addShape("roundRect", { x: M + 0.35, y: 2.35, w: 7.0, h: 0.8, rectRadius: 0.07, fill: { color: DEEP } });
  s.addText("TRAIN — April + May 2026  ·  168,352 rows", { x: M + 0.35, y: 2.35, w: 7.0, h: 0.8,
    fontFace: F, fontSize: 14, bold: true, color: "FFFFFF", align: "center", margin: 0 });
  s.addShape("roundRect", { x: M + 7.55, y: 2.35, w: 4.1, h: 0.8, rectRadius: 0.07, fill: { color: AMBER } });
  s.addText("TEST — unseen June  ·  81,588 rows", { x: M + 7.55, y: 2.35, w: 4.1, h: 0.8,
    fontFace: F, fontSize: 14, bold: true, color: "0B1220", align: "center", margin: 0 });
  // ladder
  const ladder = [
    ["FaTable", "Naive baseline", "station × weekday × hour mean — the lookup table to beat"],
    ["FaChartLine", "Linear regression", "one-hot calendar + station identity, OLS"],
    ["FaTree", "Random forest", "200 trees · min leaf 3"],
    ["FaRocket", "XGBoost", "500 trees · depth 7 · lr 0.05"],
  ];
  ladder.forEach((r, i) => {
    const x = M + i * 3.06;
    card(s, x, 3.85, 2.86, 2.15, CARD2);
    circleIcon(s, x + 0.28, 4.1, r[0], 0.56);
    s.addText(r[1], { x: x + 0.28, y: 4.85, w: 2.4, h: 0.35, fontFace: F, fontSize: 14.5,
      bold: true, color: INK, margin: 0 });
    s.addText(r[2], { x: x + 0.28, y: 5.2, w: 2.4, h: 0.7, fontFace: F, fontSize: 11,
      color: MUTED, margin: 0 });
  });
  s.addText("Identical scikit-learn pipelines · no leakage · MAE / RMSE / R² in bikes",
    { x: M, y: 6.35, w: 12, h: 0.35, fontFace: F, fontSize: 13, italic: true, color: ICE, margin: 0 });
  pageno(s, 5);
  s.addNotes("Strict temporal split: fit on April-May, evaluate once on unseen June — the honest deployment scenario. Ladder of four models so the final choice is justified.");

  // ================= 6 · RESULTS =================
  s = p.addSlide({ masterName: "DARK" });
  kicker(s, "Results — unseen June 2026");
  title(s, "Random forest wins — but the honest story is the near-tie");
  whiteImg(s, FIG + "model_comparison.png", M, 2.0, 6.9, 4.1);
  card(s, 7.9, 2.0, 4.75, 1.9, CARD);
  stat(s, 8.0, 2.2, 2.2, "4.96", "MAE (bikes) — best model", ICE);
  stat(s, 10.3, 2.2, 2.2, "0.556", "R² on unseen June", ICE);
  card(s, 7.9, 4.15, 4.75, 1.95, CARD2);
  s.addText("THE FINDING", { x: 8.2, y: 4.4, w: 4, h: 0.3, fontFace: F, fontSize: 11,
    color: BLUE, bold: true, charSpacing: 2, margin: 0 });
  s.addText("The forest only matches the weekly-rhythm lookup table — calendar structure carries almost all predictable signal. Reported as a ceiling, not hidden.",
    { x: 8.2, y: 4.75, w: 4.2, h: 1.25, fontFace: F, fontSize: 13.5, color: INK, margin: 0 });
  s.addText("Linear regression −33% worse · XGBoost underfits the 147-column one-hot space",
    { x: M, y: 6.35, w: 12, h: 0.35, fontFace: F, fontSize: 13, italic: true, color: ICE, margin: 0 });
  pageno(s, 6);
  s.addNotes("RF: MAE 4.96 bikes, R-squared 0.556 — marginally ahead of the baseline on RMSE. The instructive result is the near-tie: it quantifies how far calendar features alone go, and defines the bar richer models must clear.");

  // ================= 7 · WHEN IT FAILS =================
  s = p.addSlide({ masterName: "DARK" });
  kicker(s, "Error analysis");
  title(s, "It errs exactly where you'd forgive it — the rush shoulders");
  whiteImg(s, FIG + "error_by_hour.png", M, 2.0, 5.95, 3.6);
  whiteImg(s, FIG + "station_profile.png", 6.75, 2.0, 5.95, 3.6);
  s.addText([
    { text: "Error peaks at 08:00 and 17:00–18:00 — when availability changes fastest. ", options: { color: INK } },
    { text: "The direction of the tide is still predicted correctly, and rebalancing decisions hinge on direction, not exact counts.", options: { color: MUTED } },
  ], { x: M, y: 5.85, w: 12, h: 0.8, fontFace: F, fontSize: 14, margin: 0 });
  pageno(s, 7);
  s.addNotes("Left: error by hour peaks at the two commuter shoulders. Right: highest-swing station — the forest tracks the sharp morning drain closely. Least damaging failure profile possible.");

  // ================= 8 · BUSINESS LAYER =================
  s = p.addSlide({ masterName: "DARK" });
  kicker(s, "From forecast to action");
  title(s, "A forecast is not a decision — alerts are");
  card(s, M, 2.0, 5.8, 4.3, CARD);
  circleIcon(s, M + 0.35, 2.35, "FaBell", 0.62, GREEN);
  s.addText("Empty-risk alert = predicted ≤ 2 bikes", { x: M + 1.15, y: 2.42, w: 4.4, h: 0.5,
    fontFace: F, fontSize: 15.5, bold: true, color: INK, margin: 0 });
  stat(s, M + 0.2, 3.15, 2.7, "78%", "precision — 4 of 5 dispatches justified", GREEN);
  stat(s, M + 2.95, 3.15, 2.7, "28%", "recall — the predictable outages", ICE);
  s.addText("Tuned conservative: crew time is the scarce resource.", { x: M + 0.35, y: 5.55, w: 5.2,
    h: 0.6, fontFace: F, fontSize: 12.5, italic: true, color: MUTED, margin: 0 });
  card(s, 6.9, 2.0, 5.75, 4.3, CARD2);
  circleIcon(s, 7.25, 2.35, "FaSlidersH", 0.62, AMBER);
  s.addText("The threshold is an operations lever", { x: 8.05, y: 2.42, w: 4.4, h: 0.5,
    fontFace: F, fontSize: 15.5, bold: true, color: INK, margin: 0 });
  const lev = [
    "Lower it → fewer, higher-confidence alerts",
    "Raise it → catch more outages, spend more crew time",
    "Exposed as a slider in the dashboard — the trade-off is explicit, not hidden in code",
  ];
  s.addText(lev.map((t, i) => ({ text: t, options: { bullet: { code: "2022", indent: 14 },
    color: INK, breakLine: i < lev.length - 1, paraSpaceAfter: 10 } })),
    { x: 7.25, y: 3.3, w: 5.1, h: 2.6, fontFace: F, fontSize: 14, margin: 0 });
  pageno(s, 8);
  s.addNotes("Alerts, not numbers: 78 percent precision means four of five dispatches target a genuine problem. Recall 28 percent — deliberately conservative. The threshold is a visible lever, a management decision.");

  // ================= 9 · DASHBOARD / DEMO =================
  s = p.addSlide({ masterName: "DARK" });
  kicker(s, "The application");
  title(s, "An operations dashboard, not a notebook", 0.88, 9.5);
  s.addShape("roundRect", { x: 10.6, y: 0.82, w: 2.05, h: 0.55, rectRadius: 0.27, fill: { color: GREEN } });
  s.addText("● LIVE DEMO", { x: 10.6, y: 0.82, w: 2.05, h: 0.55, fontFace: F, fontSize: 13,
    bold: true, color: "0B1220", align: "center", margin: 0 });
  const feats = [
    ["FaMapMarkedAlt", "City map, three views", "Predicted bikes · alert status · commuter roles, for any day-hour"],
    ["FaTruck", "Rebalancing planner", "Wed 08:00 → move 26 bikes over 27.1 km to relieve 49 low stations — downloadable CSV"],
    ["FaUsers", "Station roles", "50 commuter origins · 34 destinations · 31 balanced — a capacity-planning map"],
    ["FaFlask", "Honest model page", "Metrics, confusion matrix and the threshold lever — the tool never oversells itself"],
  ];
  feats.forEach((r, i) => {
    const x = M + (i % 2) * 6.2, y = 2.0 + Math.floor(i / 2) * 2.3;
    card(s, x, y, 5.85, 2.05, CARD);
    circleIcon(s, x + 0.3, y + 0.3, r[0], 0.6);
    s.addText(r[1], { x: x + 1.1, y: y + 0.32, w: 4.5, h: 0.4, fontFace: F, fontSize: 16,
      bold: true, color: INK, margin: 0 });
    s.addText(r[2], { x: x + 1.1, y: y + 0.78, w: 4.55, h: 1.1, fontFace: F, fontSize: 12.5,
      color: MUTED, margin: 0 });
  });
  s.addText("Streamlit · reads tiny precomputed CSVs · starts instantly · never loads the 545 MB model",
    { x: M, y: 6.6, w: 12, h: 0.35, fontFace: F, fontSize: 13, italic: true, color: ICE, margin: 0 });
  pageno(s, 9);
  s.addNotes("Switch to the live app here: scenario presets, the map, then the planner — 26 bikes, 27 kilometres, one click to download the move list. Then back for ethics and close.");

  // ================= 10 · ETHICS =================
  s = p.addSlide({ masterName: "DARK" });
  kicker(s, "Ethical concerns");
  title(s, "No personal data — the ethics live in how service is steered");
  const eth = [
    ["FaUserShield", GREEN, "Privacy by design", "Aggregate counts at public infrastructure — no trips, no accounts, no individuals."],
    ["FaBalanceScale", AMBER, "Spatial equity", "Optimising for predicted demand can compound under-service at the periphery — the role and reliability views make chronic neglect visible."],
    ["FaSlidersH", BLUE, "The lever is ethical", "A precision-tuned system quietly accepts 72% of outages — and the affected riders are not randomly distributed."],
    ["FaLeaf", GREEN, "Open + efficient", "All data, code and metrics are reproducible; better routing means fewer diesel truck kilometres."],
  ];
  eth.forEach((r, i) => {
    const y = 1.95 + i * 1.22;
    circleIcon(s, M, y, r[0], 0.58, r[1]);
    s.addText(r[2], { x: M + 0.85, y: y - 0.02, w: 3.1, h: 0.55, fontFace: F, fontSize: 15.5,
      bold: true, color: INK, margin: 0 });
    s.addText(r[3], { x: 4.55, y: y - 0.02, w: 8.1, h: 1.05, fontFace: F, fontSize: 13,
      color: ICE, margin: 0 });
  });
  pageno(s, 10);
  s.addNotes("The feed holds no personal data by design. The real ethics: where the trucks go. Spatial equity, the precision-recall lever as an ethical choice, and full transparency.");

  // ================= 11 · CONCLUSION =================
  s = p.addSlide({ masterName: "DARK" });
  s.addShape("ellipse", { x: -3.2, y: 3.9, w: 9, h: 9, fill: { color: "0E1B33" } });
  kicker(s, "Conclusion");
  title(s, "Open data + honest ML = decisions a crew can act on");
  const take = [
    "Forecasts within ~5 bikes on a month the model never saw",
    "78%-precision alerts and a concrete, downloadable rebalancing plan",
    "The near-tie with the baseline is the finding: the weekly rhythm is the signal",
  ];
  take.forEach((t, i) => {
    const y = 2.05 + i * 0.95;
    circleIcon(s, M, y, "FaCheckCircle", 0.5, GREEN);
    s.addText(t, { x: M + 0.75, y: y - 0.03, w: 7.0, h: 0.85, fontFace: F, fontSize: 15.5,
      color: INK, margin: 0 });
  });
  card(s, 8.6, 1.95, 4.05, 3.0, CARD2);
  s.addText("NEXT", { x: 8.9, y: 2.2, w: 3, h: 0.3, fontFace: F, fontSize: 11, color: BLUE,
    bold: true, charSpacing: 2, margin: 0 });
  const fut = [["FaCloudSun", "Weather + lagged features for the rush shoulders"],
    ["FaChartLine", "Probabilistic alerts with calibrated confidence"],
    ["FaRoute", "Couple the planner to a vehicle-routing optimiser"]];
  fut.forEach((r, i) => {
    const y = 2.55 + i * 0.78;
    circleIcon(s, 8.9, y, r[0], 0.46);
    s.addText(r[1], { x: 9.5, y: y - 0.04, w: 3.05, h: 0.7, fontFace: F, fontSize: 12,
      color: ICE, margin: 0 });
  });
  s.addText("Thank you — questions welcome", { x: M, y: 5.65, w: 8, h: 0.5, fontFace: F,
    fontSize: 20, bold: true, color: INK, margin: 0 });
  s.addText("Data: Smart Dublin open data portal · dublinbikes station status, Apr–Jun 2026",
    { x: M, y: 6.25, w: 10, h: 0.35, fontFace: F, fontSize: 11.5, color: MUTED, margin: 0 });
  pageno(s, 11);
  s.addNotes("Close: within five bikes on an unseen month, alerts a crew can trust, and an honest ceiling reported as a finding. Thank you.");

  await p.writeFile({ fileName: OUT });
  console.log("WROTE", OUT);
})().catch(e => { console.error(e); process.exit(1); });
