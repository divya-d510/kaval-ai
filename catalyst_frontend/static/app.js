// ============================================================================
// KAVAL AI — Catalyst-native frontend (no WebSocket; every action is a plain
// fetch() request/response, which is what works within Catalyst AppSail's
// request-based model).
// ============================================================================

const API_URL = window.API_URL;

const ROLES = ["Investigator", "Analyst", "Supervisor", "Policymaker"];
const PERMISSIONS = {
  query: ["Investigator", "Analyst", "Supervisor"],
  analytics: ["Investigator", "Analyst", "Supervisor", "Policymaker"],
  graph: ["Investigator", "Analyst", "Supervisor"],
  profiling: ["Investigator", "Analyst", "Supervisor"],
  sociological: ["Investigator", "Analyst", "Supervisor", "Policymaker"],
  financial: ["Supervisor"],
  forecast: ["Investigator", "Analyst", "Supervisor", "Policymaker"],
  decision_support: ["Investigator", "Analyst", "Supervisor"],
  audit_log: ["Supervisor"],
};
const NAV_ITEMS = [
  ["query", "🔍 Ask a Question"],
  ["analytics", "📊 Dashboard"],
  ["graph", "🕸️ Suspect Network"],
  ["profiling", "🧬 Offender Profiling"],
  ["sociological", "🏛️ Sociological Insights"],
  ["forecast", "📈 Forecast & Early Warning"],
  ["decision_support", "🗂️ Case Decision Support"],
  ["financial", "💰 Financial Network"],
  ["audit_log", "🧾 Audit Log"],
];

let ROLE = localStorage.getItem("kaval_role") || "Investigator";
let conversation = JSON.parse(localStorage.getItem("kaval_conversation") || "[]");
let selectedSection = "query";

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------
async function apiGet(path, params) {
  const url = new URL(API_URL + path, window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && v !== null && url.searchParams.set(k, v));
  const res = await fetch(url, { headers: { "X-User-Role": ROLE } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(API_URL + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User-Role": ROLE },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Small DOM helpers
// ---------------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const el = (tag, attrs = {}, children = []) => {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  });
  (Array.isArray(children) ? children : [children]).forEach((c) => {
    if (typeof c === "string") node.appendChild(document.createTextNode(c));
    else if (c) node.appendChild(c);
  });
  return node;
};

function spinner(container, text) {
  container.innerHTML = "";
  container.appendChild(el("div", { class: "spinner" }, `⏳ ${text}`));
}
function showError(container, err) {
  container.innerHTML = "";
  container.appendChild(el("div", { class: "error-box" }, `API error: ${err.message || err}`));
}
function dataTable(rows, columns) {
  if (!rows || rows.length === 0) return el("p", { class: "caption" }, "No data.");
  const cols = columns || Object.keys(rows[0]);
  const thead = el("tr", {}, cols.map((c) => el("th", {}, c)));
  const tbody = rows.map((r) => el("tr", {}, cols.map((c) => el("td", {}, String(r[c] ?? "")))));
  const table = el("table", { class: "data-table" });
  table.appendChild(el("thead", {}, thead));
  const tb = el("tbody");
  tbody.forEach((r) => tb.appendChild(r));
  table.appendChild(tb);
  return table;
}
function metricRow(items) {
  return el("div", { class: "metric-row" }, items.map(([label, value]) =>
    el("div", { class: "metric-card" }, [el("div", { class: "label" }, label), el("div", { class: "value" }, String(value))])
  ));
}
let plotCounter = 0;
function plotDiv(height) {
  const id = `plot-${plotCounter++}`;
  return el("div", { id, class: "chart-box", style: `height:${height || 360}px` });
}

// ---------------------------------------------------------------------------
// Sidebar: role + navigation
// ---------------------------------------------------------------------------
function renderRoleSelect() {
  const sel = $("#role-select");
  sel.innerHTML = "";
  ROLES.forEach((r) => sel.appendChild(el("option", { value: r, ...(r === ROLE ? { selected: "selected" } : {}) }, r)));
  sel.addEventListener("change", () => {
    ROLE = sel.value;
    localStorage.setItem("kaval_role", ROLE);
    renderNav();
    if (!PERMISSIONS[selectedSection].includes(ROLE)) selectSection("query");
  });
}

function renderNav() {
  const list = $("#nav-list");
  list.innerHTML = "";
  NAV_ITEMS.filter(([key]) => PERMISSIONS[key].includes(ROLE)).forEach(([key, label]) => {
    const item = el("div", { class: "nav-item" + (key === selectedSection ? " active" : "") }, label);
    item.addEventListener("click", () => selectSection(key));
    list.appendChild(item);
  });
}

function selectSection(key) {
  selectedSection = key;
  document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
  $("#section-" + key).classList.remove("hidden");
  renderNav();
}

// ============================================================================
// Ask a Question
// ============================================================================
function saveConversation() {
  localStorage.setItem("kaval_conversation", JSON.stringify(conversation));
}

function speak(text, lang) {
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang === "kn" ? "kn-IN" : "en-IN";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

function renderConversation() {
  const actions = $("#chat-actions");
  actions.classList.toggle("hidden", conversation.length === 0);

  const thread = $("#chat-thread");
  thread.innerHTML = "";
  [...conversation].reverse().forEach((turn) => {
    thread.appendChild(el("div", { class: "chat-msg user" }, [el("div", { class: "chat-avatar" }, "🧑"), el("div", { class: "chat-body" }, turn.question)]));

    const body = el("div", { class: "chat-body" });
    body.appendChild(el("div", {}, turn.answer));
    const speakBtn = el("button", { class: "btn btn-secondary speak-btn", type: "button" }, "🔊 Listen");
    speakBtn.addEventListener("click", () => speak(turn.answer, turn.language));
    body.appendChild(speakBtn);
    if (turn.rows && turn.rows.length) body.appendChild(dataTable(turn.rows));
    const details = el("details", { class: "sql-details" });
    details.appendChild(el("summary", {}, "Generated SQL"));
    details.appendChild(el("div", { class: "sql-block" }, turn.sql || ""));
    if (turn.explanation) details.appendChild(el("p", { class: "caption" }, turn.explanation));
    body.appendChild(details);

    thread.appendChild(el("div", { class: "chat-msg assistant" }, [el("div", { class: "chat-avatar" }, "🤖"), body]));
  });
}

async function askQuestion() {
  const input = $("#question-input");
  const question = input.value.trim();
  if (!question) return;
  const askBtn = $("#ask-btn");
  askBtn.disabled = true;
  askBtn.textContent = "Asking...";
  try {
    const history = conversation.slice(-4).map((t) => ({ question: t.question, answer: t.answer }));
    const result = await apiPost("/query", { question, history });
    conversation.push(result);
    saveConversation();
    renderConversation();
    input.value = "";
  } catch (err) {
    alert("API error: " + err.message);
  } finally {
    askBtn.disabled = false;
    askBtn.textContent = "Ask";
  }
}

async function exportPdf() {
  const btn = $("#export-pdf-btn");
  btn.disabled = true;
  try {
    const res = await fetch(API_URL + "/export-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-Role": ROLE },
      body: JSON.stringify({ conversation: conversation.map((t) => ({ question: t.question, answer: t.answer, sql: t.sql || "" })) }),
    });
    if (!res.ok) throw new Error(`API error ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kaval_ai_conversation_${Date.now()}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert("Export failed: " + err.message);
  } finally {
    btn.disabled = false;
  }
}

function setupVoiceInput() {
  const btn = $("#voice-record-btn");
  const out = $("#voice-out");
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    btn.addEventListener("click", () => (out.textContent = "Speech recognition not supported in this browser."));
    return;
  }
  btn.addEventListener("click", () => {
    const lang = document.querySelector('input[name="voice-lang"]:checked').value;
    const rec = new SR();
    rec.lang = lang;
    rec.interimResults = false;
    out.textContent = "Listening...";
    rec.start();
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      out.textContent = "Heard: " + text;
      $("#question-input").value = text;
    };
    rec.onerror = (e) => (out.textContent = "Error: " + e.error);
  });
}

// ============================================================================
// Dashboard
// ============================================================================
async function loadDashboard() {
  const out = $("#dashboard-output");
  spinner(out, "Computing statistics...");
  try {
    const lang = document.querySelector('input[name="dash-lang"]:checked').value;
    const stats = await apiGet("/analytics", { language: lang, summary: true });
    out.innerHTML = "";
    out.appendChild(el("div", { class: "info-box" }, stats.summary));
    out.appendChild(metricRow([
      ["Total FIRs", stats.total_firs],
      ["Districts", Object.keys(stats.by_district).length],
      ["Open cases", stats.by_status.Open || 0],
    ]));

    const grid = el("div", { class: "chart-grid" });
    const p1 = plotDiv(), p2 = plotDiv();
    grid.appendChild(p1); grid.appendChild(p2);
    out.appendChild(grid);
    const p3 = plotDiv();
    out.appendChild(p3);
    const grid2 = el("div", { class: "chart-grid" });
    const p4 = plotDiv(), p5 = plotDiv();
    grid2.appendChild(p4); grid2.appendChild(p5);
    out.appendChild(grid2);

    Plotly.newPlot(p1.id, [{ x: Object.keys(stats.by_crime_type), y: Object.values(stats.by_crime_type), type: "bar", marker: { color: "#ff4b4b" } }],
      { title: "FIRs by Crime Type", margin: { t: 40 } }, { responsive: true });
    Plotly.newPlot(p2.id, [{ labels: Object.keys(stats.by_district), values: Object.values(stats.by_district), type: "pie" }],
      { title: "FIRs by District", margin: { t: 40 } }, { responsive: true });
    const months = Object.keys(stats.by_month).sort();
    Plotly.newPlot(p3.id, [{ x: months, y: months.map((m) => stats.by_month[m]), type: "scatter", mode: "lines+markers", line: { color: "#ff4b4b" } }],
      { title: "FIRs per Month", margin: { t: 40 } }, { responsive: true });
    const topAreas = Object.entries(stats.top_areas);
    Plotly.newPlot(p4.id, [{ x: topAreas.map((a) => a[1]), y: topAreas.map((a) => a[0]), type: "bar", orientation: "h", marker: { color: "#ff4b4b" } }],
      { title: "Top 10 Hotspot Areas", margin: { t: 40, l: 140 } }, { responsive: true });
    Plotly.newPlot(p5.id, [{ labels: Object.keys(stats.by_status), values: Object.values(stats.by_status), type: "pie", hole: 0.4 }],
      { title: "Case Status", margin: { t: 40 } }, { responsive: true });
  } catch (err) {
    showError(out, err);
  }
}

// ============================================================================
// Suspect Network
// ============================================================================
async function buildNetwork() {
  const out = $("#graph-output");
  spinner(out, "Building graph...");
  try {
    const includeVictims = $("#include-victims-cb").checked;
    const g = await apiGet("/graph", { include_victims: includeVictims });
    out.innerHTML = "";
    const stats = g.stats;
    out.appendChild(metricRow([
      ["Suspects", stats.num_suspects], ["Locations", stats.num_locations], ["Victims", stats.num_victims],
      ["Links", stats.num_links], ["Groups", stats.num_communities],
    ]));

    const pos = {};
    g.nodes.forEach((n) => (pos[n.id] = [n.x, n.y]));
    const edgeX = [], edgeY = [];
    g.edges.forEach((e) => {
      const [x0, y0] = pos[e.source], [x1, y1] = pos[e.target];
      edgeX.push(x0, x1, null); edgeY.push(y0, y1, null);
    });
    const traces = [{ x: edgeX, y: edgeY, mode: "lines", line: { width: 0.5, color: "#cbd5e1" }, hoverinfo: "none", showlegend: false }];

    const suspects = g.nodes.filter((n) => n.type === "suspect");
    if (suspects.length) traces.push({
      x: suspects.map((n) => n.x), y: suspects.map((n) => n.y), mode: "markers", name: "Suspects", type: "scatter",
      marker: { size: suspects.map((n) => 8 + 3 * n.prior_cases), color: suspects.map((n) => n.community), colorscale: "Turbo", line: { width: 1, color: "white" } },
      text: suspects.map((n) => `${n.name} (${n.id})<br>Prior cases: ${n.prior_cases}<br>Connections: ${n.degree}`), hoverinfo: "text",
    });
    const locations = g.nodes.filter((n) => n.type === "location");
    if (locations.length) traces.push({
      x: locations.map((n) => n.x), y: locations.map((n) => n.y), mode: "markers", name: "Locations", type: "scatter",
      marker: { size: 14, color: "#111827", symbol: "diamond", line: { width: 1, color: "white" } },
      text: locations.map((n) => `📍 ${n.name}<br>Connections: ${n.degree}`), hoverinfo: "text",
    });
    const victims = g.nodes.filter((n) => n.type === "victim");
    if (victims.length) traces.push({
      x: victims.map((n) => n.x), y: victims.map((n) => n.y), mode: "markers", name: "Victims", type: "scatter",
      marker: { size: 7, color: "#a855f7", line: { width: 1, color: "white" } },
      text: victims.map((n) => `🧍 ${n.name}`), hoverinfo: "text",
    });

    const p = plotDiv(650);
    out.appendChild(p);
    Plotly.newPlot(p.id, traces, { showlegend: true, height: 650, xaxis: { visible: false }, yaxis: { visible: false }, margin: { l: 10, r: 10, t: 10, b: 10 } }, { responsive: true });

    out.appendChild(el("h3", {}, "Most connected suspects (network centrality)"));
    out.appendChild(dataTable(stats.top_central));
  } catch (err) {
    showError(out, err);
  }
}

// ============================================================================
// Offender Profiling
// ============================================================================
async function loadPriorityList() {
  const out = $("#priority-list-output");
  spinner(out, "Scoring suspects...");
  try {
    const data = await apiGet("/profiling/top", { limit: 15 });
    out.innerHTML = "";
    out.appendChild(el("h3", {}, "Priority Investigation List (highest risk first)"));
    out.appendChild(dataTable(data.suspects));
  } catch (err) {
    showError(out, err);
  }
}

async function buildProfile() {
  const suspectId = $("#suspect-id-input").value.trim();
  if (!suspectId) return;
  const out = $("#profile-output");
  spinner(out, "Building profile...");
  try {
    const profile = await apiGet(`/profiling/${encodeURIComponent(suspectId)}`);
    out.innerHTML = "";
    if (profile.error) { out.appendChild(el("div", { class: "error-box" }, profile.error)); return; }

    out.appendChild(metricRow([["Risk score", `${profile.risk_score} / 100`]]));
    out.appendChild(el("p", {}, el("b", {}, "Modus operandi: ") ), );
    out.lastChild.appendChild(document.createTextNode(profile.modus_operandi));

    const breakdown = Object.entries(profile.risk_breakdown).map(([k, v]) => [k.replace(/_/g, " "), v.contribution]);
    const p = plotDiv();
    out.appendChild(p);
    Plotly.newPlot(p.id, [{ x: breakdown.map((b) => b[1]), y: breakdown.map((b) => b[0]), type: "bar", orientation: "h", marker: { color: "#ff4b4b" } }],
      { title: "Risk score breakdown (points out of 100)", margin: { t: 40, l: 160 } }, { responsive: true });

    out.appendChild(el("h3", {}, "Behavioral summary"));
    out.appendChild(el("div", { class: "info-box" }, profile.behavioral_summary));
    out.appendChild(el("h3", {}, "Case history"));
    out.appendChild(dataTable(profile.case_history));
  } catch (err) {
    showError(out, err);
  }
}

// ============================================================================
// Sociological Insights
// ============================================================================
async function loadSociological() {
  const out = $("#sociological-output");
  spinner(out, "Analyzing demographics...");
  try {
    const lang = document.querySelector('input[name="socio-lang"]:checked').value;
    const data = await apiGet("/sociological", { language: lang });
    out.innerHTML = "";
    out.appendChild(el("div", { class: "info-box" }, data.summary));

    const grid = el("div", { class: "chart-grid" });
    const p1 = plotDiv(), p2 = plotDiv();
    grid.appendChild(p1); grid.appendChild(p2);
    out.appendChild(grid);
    const p3 = plotDiv();
    out.appendChild(p3);

    Plotly.newPlot(p1.id, [{ labels: Object.keys(data.by_gender), values: Object.values(data.by_gender), type: "pie" }], { title: "Accused by Gender", margin: { t: 40 } }, { responsive: true });
    Plotly.newPlot(p2.id, [{ labels: Object.keys(data.by_socio_economic_band), values: Object.values(data.by_socio_economic_band), type: "pie" }], { title: "Accused by Socio-Economic Band", margin: { t: 40 } }, { responsive: true });
    Plotly.newPlot(p3.id, [{ x: Object.keys(data.by_education_level), y: Object.values(data.by_education_level), type: "bar", marker: { color: "#ff4b4b" } }], { title: "Accused by Education Level", margin: { t: 40 } }, { responsive: true });

    const bands = Object.keys(data.crime_type_by_socio_band);
    if (bands.length) {
      const p4 = plotDiv();
      out.appendChild(p4);
      const crimeTypes = [...new Set(bands.flatMap((b) => Object.keys(data.crime_type_by_socio_band[b])))];
      const traces = bands.map((band) => ({
        x: crimeTypes, y: crimeTypes.map((c) => data.crime_type_by_socio_band[band][c] || 0), type: "bar", name: band,
      }));
      Plotly.newPlot(p4.id, traces, { barmode: "group", title: "Crime Type by Socio-Economic Band", margin: { t: 40 } }, { responsive: true });
    }

    const areaEntries = Object.entries(data.area_low_band_share).sort((a, b) => b[1] - a[1]).slice(0, 10);
    const p5 = plotDiv();
    out.appendChild(p5);
    Plotly.newPlot(p5.id, [{ x: areaEntries.map((a) => a[1]), y: areaEntries.map((a) => a[0]), type: "bar", orientation: "h", marker: { color: "#ff4b4b" } }],
      { title: "Top areas by share of accused from Low socio-economic band", margin: { t: 40, l: 160 } }, { responsive: true });

    out.appendChild(el("p", { class: "caption" }, "Observed correlations in this dataset only — not causal claims."));
  } catch (err) {
    showError(out, err);
  }
}

// ============================================================================
// Forecast & Early Warning
// ============================================================================
async function runForecast() {
  const out = $("#forecast-output");
  spinner(out, "Projecting trends...");
  try {
    const data = await apiGet("/forecast");
    out.innerHTML = "";
    if (data.early_warnings.length) {
      const box = el("div", { class: "warning-box" }, `⚠️ ${data.early_warnings.length} district/crime-type combination(s) flagged for an accelerating trend:`);
      data.early_warnings.forEach((w) => box.appendChild(el("div", {}, `• ${w.district} — ${w.crime_type}: projected ${w.next_month_projection} next month (recent trend slope ${w.trend_slope})`)));
      out.appendChild(box);
    } else {
      out.appendChild(el("div", { class: "success-box" }, "No early-warning combinations detected in the current window."));
    }

    const top15 = data.projections.slice(0, 15);
    const p = plotDiv();
    out.appendChild(p);
    Plotly.newPlot(p.id, [{
      x: top15.map((r) => r.trend_slope), y: top15.map((r) => `${r.district} — ${r.crime_type}`), type: "bar", orientation: "h",
      marker: { color: top15.map((r) => (r.early_warning ? "#dc2626" : "#94a3b8")) },
    }], { title: "Trend slope by district/crime type (top 15)", margin: { t: 40, l: 220 } }, { responsive: true });

    out.appendChild(dataTable(data.projections.map((r) => ({
      district: r.district, crime_type: r.crime_type, monthly_counts: JSON.stringify(r.monthly_counts),
      trend_slope: r.trend_slope, next_month_projection: r.next_month_projection, early_warning: r.early_warning,
    }))));
  } catch (err) {
    showError(out, err);
  }
}

// ============================================================================
// Case Decision Support
// ============================================================================
async function buildCaseSummary() {
  const firId = $("#fir-id-input").value.trim();
  if (!firId) return;
  const out = $("#case-output");
  spinner(out, "Summarizing case...");
  try {
    const data = await apiGet(`/case-summary/${encodeURIComponent(firId)}`);
    out.innerHTML = "";
    if (data.error) { out.appendChild(el("div", { class: "error-box" }, data.error)); return; }

    const fir = data.fir;
    out.appendChild(el("h3", {}, `${fir.fir_id} — ${fir.crime_type} (${fir.status})`));
    out.appendChild(el("p", {}, `Filed: ${fir.date_filed} · ${fir.police_station}, ${fir.district}, ${fir.area}`));
    out.appendChild(el("p", {}, fir.description));

    out.appendChild(el("h3", {}, "AI case summary & suggested leads"));
    out.appendChild(el("div", { class: "info-box" }, data.narrative));

    const grid = el("div", { class: "chart-grid" });
    const accusedBox = el("div"); accusedBox.appendChild(el("h4", {}, "Accused")); accusedBox.appendChild(dataTable(data.accused));
    const victimsBox = el("div"); victimsBox.appendChild(el("h4", {}, "Victims")); victimsBox.appendChild(dataTable(data.victims));
    grid.appendChild(accusedBox); grid.appendChild(victimsBox);
    out.appendChild(grid);

    out.appendChild(el("h3", {}, "Similar past cases"));
    out.appendChild(dataTable(data.similar_cases));
  } catch (err) {
    showError(out, err);
  }
}

// ============================================================================
// Financial Network (Supervisor only)
// ============================================================================
async function loadFinancial() {
  const out = $("#financial-output");
  spinner(out, "Analyzing transactions...");
  try {
    const data = await apiGet("/financial");
    out.innerHTML = "";
    const s = data.stats;
    out.appendChild(metricRow([
      ["Accounts", s.num_accounts], ["Transactions", s.num_transactions],
      ["Flagged transactions", s.num_flagged_transactions], ["Possible mule accounts", s.num_mule_accounts],
      ["Total flagged amount (Rs.)", s.total_flagged_amount.toLocaleString()],
    ]));

    out.appendChild(el("h3", {}, "Flagged transactions"));
    out.appendChild(dataTable(data.flagged_transactions));

    // simple force-free layout: place nodes on a circle (no client-side graph layout library)
    const n = data.nodes.length;
    const pos = {};
    data.nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(n, 1);
      pos[node.id] = [Math.cos(angle), Math.sin(angle)];
    });
    const edgeX = [], edgeY = [];
    data.edges.forEach((e) => {
      if (pos[e.source] && pos[e.target]) {
        edgeX.push(pos[e.source][0], pos[e.target][0], null);
        edgeY.push(pos[e.source][1], pos[e.target][1], null);
      }
    });
    const p = plotDiv(550);
    out.appendChild(p);
    Plotly.newPlot(p.id, [
      { x: edgeX, y: edgeY, mode: "lines", line: { width: 0.4, color: "#cbd5e1" }, hoverinfo: "none", showlegend: false },
      {
        x: data.nodes.map((nd) => pos[nd.id][0]), y: data.nodes.map((nd) => pos[nd.id][1]), mode: "markers", type: "scatter",
        marker: { size: data.nodes.map((nd) => (nd.flagged_mule ? 16 : 9)), color: data.nodes.map((nd) => (nd.flagged_mule ? "#dc2626" : "#2563eb")), line: { width: 1, color: "white" } },
        text: data.nodes.map((nd) => `${nd.name} — ${nd.bank} (${nd.type})${nd.flagged_mule ? " ⚠️ possible mule" : ""}`), hoverinfo: "text",
      },
    ], { showlegend: false, height: 550, xaxis: { visible: false }, yaxis: { visible: false }, margin: { l: 10, r: 10, t: 10, b: 10 } }, { responsive: true });
  } catch (err) {
    showError(out, err);
  }
}

// ============================================================================
// Audit Log (Supervisor only)
// ============================================================================
async function loadAuditLog() {
  const out = $("#audit-output");
  spinner(out, "Loading...");
  try {
    const data = await apiGet("/audit-log", { limit: 200 });
    out.innerHTML = "";
    out.appendChild(dataTable(data.entries, ["log_id", "logged_at", "role", "endpoint", "summary"]));
  } catch (err) {
    showError(out, err);
  }
}

// ============================================================================
// Wiring
// ============================================================================
document.addEventListener("DOMContentLoaded", () => {
  renderRoleSelect();
  renderNav();
  selectSection("query");
  renderConversation();
  setupVoiceInput();

  $("#example-select").addEventListener("change", (e) => {
    if (e.target.value) $("#question-input").value = e.target.value;
  });
  $("#ask-btn").addEventListener("click", askQuestion);
  $("#question-input").addEventListener("keydown", (e) => { if (e.key === "Enter") askQuestion(); });
  $("#clear-btn").addEventListener("click", () => { conversation = []; saveConversation(); renderConversation(); });
  $("#export-pdf-btn").addEventListener("click", exportPdf);

  $("#load-dashboard-btn").addEventListener("click", loadDashboard);
  $("#build-network-btn").addEventListener("click", buildNetwork);
  $("#load-priority-btn").addEventListener("click", loadPriorityList);
  $("#build-profile-btn").addEventListener("click", buildProfile);
  $("#load-sociological-btn").addEventListener("click", loadSociological);
  $("#run-forecast-btn").addEventListener("click", runForecast);
  $("#build-case-btn").addEventListener("click", buildCaseSummary);
  $("#load-financial-btn").addEventListener("click", loadFinancial);
  $("#refresh-audit-btn").addEventListener("click", loadAuditLog);
});
