const $ = (id) => document.getElementById(id);
const api = (path, opts) => fetch(path, opts).then((r) => r.json());

let map, marker, lastInv, events = [];

function initMap() {
  map = L.map("map", { zoomControl: true, attributionControl: true }).setView([10, 40], 3);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{png}".replace("{png}", "png"), {
    attribution: "© OpenStreetMap © CARTO",
  }).addTo(map);
}

async function boot() {
  initMap();
  try {
    const h = await api("/api/health");
    $("health").textContent = h.ok ? "API: connected" : "API: unexpected";
  } catch {
    $("health").textContent = "API: start with python -m jaadu serve";
  }
  const regions = await api("/api/regions");
  $("region").innerHTML = regions.map((r) => `<option value="${r.id}">${r.name} (${r.country})</option>`).join("");
  events = await api("/api/events");
  $("event").innerHTML = events.map((e) => `<option value="${e.id}">${e.title}</option>`).join("");
  $("event").addEventListener("change", syncEvent);
  $("run").addEventListener("click", () => run($("asof").value));
  $("reveal").addEventListener("click", reveal);
  $("slider").addEventListener("input", onSlide);
  $("perturb").addEventListener("click", doPerturb);
  $("ablate").addEventListener("click", doAblate);
  syncEvent();
  renderBenchmark();
}

function syncEvent() {
  const ev = events.find((e) => e.id === $("event").value);
  if (!ev) return;
  $("region").value = ev.region;
  $("asof").value = ev.prediction_cutoff;
  const months = monthRange("2013-01-01", ev.conventional_visible_date);
  $("slider").max = String(months.length - 1);
  $("slider").value = String(Math.max(0, months.findIndex((m) => m >= ev.prediction_cutoff)));
  $("slider").dataset.months = JSON.stringify(months);
  $("sliderLabel").textContent = $("asof").value;
  const region = [...$("region").options].find((o) => o.value === ev.region);
  $("regionNote").textContent = ev.conventional_headline;
}

function monthRange(a, b) {
  const out = [];
  let d = new Date(a);
  const end = new Date(b);
  while (d <= end) {
    out.push(d.toISOString().slice(0, 10));
    d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1));
  }
  return out;
}

function onSlide() {
  const months = JSON.parse($("slider").dataset.months || "[]");
  const v = months[Number($("slider").value)];
  if (v) {
    $("asof").value = v;
    $("sliderLabel").textContent = v;
  }
}

async function run(asOf) {
  $("risk").innerHTML = "<p class='muted'>Running discovery engine… this is computation, not a canned animation.</p>";
  $("reveal").disabled = true;
  $("outcome").classList.add("hidden");
  const region = $("region").value;
  const inv = await api(`/api/investigate?region=${encodeURIComponent(region)}&as_of=${asOf}`);
  if (inv.error) {
    $("risk").textContent = JSON.stringify(inv);
    return;
  }
  lastInv = inv;
  renderAll(inv);
  $("reveal").disabled = false;
}

function renderAll(inv) {
  const r = inv.region;
  if (marker) map.removeLayer(marker);
  const c = r.centroid;
  map.setView([c.lat, c.lon], 6);
  marker = L.circleMarker([c.lat, c.lon], { radius: 10, color: "#e0a14a" }).addTo(map);
  $("regionNote").textContent = r.why || "";
  const rep = inv.report;
  const alert = inv.detection.multi_signal_alert;
  $("risk").innerHTML = `
    <p><span class="pill ${alert ? "warn" : "ok"}">${rep.risk}</span>
    <span class="pill">${rep.intervention_vs_investigation}</span></p>
    <p>Detection time <b>${rep.detection_time}</b>. Earliest persistent signal: <b>${rep.earliest_signal || "none"}</b>.</p>
    <p class="muted">${rep.confidence.meaning}</p>
    <p>Data quality: ${rep.confidence.data_quality} · Detection: ${rep.confidence.detection_confidence} · Causal: ${rep.confidence.causal_confidence}</p>
    <p>${rep.current_signals.map((s) => `<span class="pill ${s.strong ? "bad" : "warn"}">${s.variable} z=${s.seasonal_z.toFixed(2)}${s.persistent ? " persist" : ""}</span>`).join("")}</p>
  `;
  renderTimeline(inv);
  renderGraph(inv);
  renderHyps(inv);
  renderEvidence(inv);
  renderCf(inv);
  renderVoi(inv);
  renderReport(inv);
  $("pvar").innerHTML = (inv.detection.current_signals || []).map((s) => `<option>${s.variable}</option>`).join("")
    || `<option>rainfall</option>`;
}

function renderTimeline(inv) {
  const rows = inv.z_tail || [];
  if (!rows.length) {
    $("timeline").textContent = "No seasonal z series.";
    return;
  }
  const vars = Object.keys(rows[0]).filter((k) => k !== "timestamp" && k !== "index");
  const focus = (inv.detection.current_signals || []).map((s) => s.variable);
  const show = [...new Set([...focus, ...vars])].slice(0, 8);
  $("timeline").innerHTML = show.map((v) => {
    const vals = rows.map((row) => Number(row[v]));
    const w = 520, h = 28;
    const pts = vals.map((z, i) => {
      const x = (i / Math.max(vals.length - 1, 1)) * w;
      const y = h / 2 - (Number.isFinite(z) ? Math.max(-2.8, Math.min(2.8, z)) / 2.8 : 0) * (h / 2 - 2);
      return `${x},${y}`;
    }).join(" ");
    return `<div class="tl"><div>${v}</div><svg class="spark" width="${w}" height="${h}"><polyline fill="none" stroke="#6ec8c5" stroke-width="1.4" points="${pts}" /></svg></div>`;
  }).join("");
}

const TYPE_COLOR = {
  CLIMATE: "#6ec8c5",
  WATER: "#4c8fd4",
  AGRICULTURE: "#8fb389",
  MARKET: "#e0a14a",
  ENERGY: "#d36b6b",
  TRANSPORT: "#c4a4de",
};

function renderGraph(inv) {
  const svg = $("graph");
  const nodes = inv.graph.nodes.filter((n) => n.seasonal_z != null || n.n_obs > 0).slice(0, 14);
  const ids = new Set(nodes.map((n) => n.node_id));
  const edges = inv.graph.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
  const cols = {};
  nodes.forEach((n) => {
    cols[n.node_type] = cols[n.node_type] || [];
    cols[n.node_type].push(n);
  });
  const types = Object.keys(cols);
  const pos = {};
  types.forEach((t, i) => {
    const x = 70 + i * (680 / Math.max(types.length, 1));
    cols[t].forEach((n, j) => {
      pos[n.node_id] = { x, y: 50 + j * 55, n };
    });
  });
  let html = "";
  edges.forEach((e) => {
    const a = pos[e.source], b = pos[e.target];
    if (!a || !b) return;
    const weak = e.causal_status === "correlation";
    html += `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${weak ? "#5a6578" : "#e0a14a"}" stroke-width="${1 + 3 * Math.abs(e.strength)}" data-edge='${JSON.stringify(e)}' />`;
  });
  nodes.forEach((n) => {
    const p = pos[n.node_id];
    const z = n.seasonal_z;
    const r = 8 + Math.min(10, Math.abs(z || 0) * 2);
    html += `<g class="node" data-node="${n.node_id}">
      <circle cx="${p.x}" cy="${p.y}" r="${r}" fill="${TYPE_COLOR[n.node_type] || "#999"}" opacity="0.9" />
      <text x="${p.x + 14}" y="${p.y + 4}" fill="#f3efe6" font-size="11">${n.variable}</text>
    </g>`;
  });
  svg.innerHTML = html;
  svg.querySelectorAll("line").forEach((ln) => {
    ln.addEventListener("click", () => {
      const e = JSON.parse(ln.dataset.edge);
      $("edgeCard").innerHTML = `<b>${e.source} → ${e.target}</b> lag ${e.lag_months}m · strength ${e.strength.toFixed(2)} · p=${e.p_value != null ? e.p_value.toFixed(3) : "n/a"} · ${e.causal_status} · ${e.method} · stability ${e.historical_stability.toFixed(2)}<p class="muted">${inv.graph.method_notes}</p>`;
    });
  });
}

function renderHyps(inv) {
  $("hyps").innerHTML = inv.hypotheses.slice(0, 5).map((h, i) => `
    <div class="hyp ${i === 0 ? "lead" : ""}">
      <div><b>${h.score.rank}. ${h.label}</b> · posterior ${(h.score.posterior * 100).toFixed(1)}%</div>
      <div class="muted">${h.statement}</div>
      <div class="bar"><i style="width:${Math.round(h.score.posterior * 100)}%"></i></div>
      <div class="fine">support ${h.score.supporting.toFixed(2)} · contradict ${h.score.contradictory.toFixed(2)} · temporal ${h.score.temporal_consistency.toFixed(2)} · ${h.causal_status}</div>
      ${h.unknown_variables.length ? `<div class="fine">Unknown: ${h.unknown_variables.join(", ")}</div>` : ""}
    </div>
  `).join("") + `<p class="fine">Adversary: ${inv.challenge.verdict}. ${(inv.challenge.attacks || []).join(" ")}</p>`;
}

function renderEvidence(inv) {
  const ev = inv.evidence || [];
  if (!ev.length) {
    $("evidence").innerHTML = "<p class='muted'>No textual evidence admitted at this cutoff (publication dates respected).</p>";
    return;
  }
  $("evidence").innerHTML = ev.map((e) => `
    <div class="ev">
      <div><span class="pill">${e.extraction_kind}</span> ${e.claim}</div>
      <div class="fine">${e.source} · published ${e.published_at} · ${e.geographic_scope}</div>
      <blockquote class="fine">${e.supporting_passage}</blockquote>
    </div>
  `).join("");
}

function renderCf(inv) {
  const cf = inv.counterfactuals || {};
  $("cf").innerHTML = Object.entries(cf).map(([k, v]) => {
    const m = v.matched || {};
    return `<div class="ev"><b>${k}</b><div class="fine">${m.interpretation || m.reason || ""}</div>
      <div class="fine">Status: ${m.status}. ${((m.assumptions) || []).join(" ")}</div></div>`;
  }).join("");
}

function renderVoi(inv) {
  $("voi").innerHTML = (inv.voi || []).slice(0, 6).map((v) => `
    <div class="voi-row">
      <b>#${v.rank} ${v.label}</b>
      <div class="fine">EIG ${v.expected_information_gain.toFixed(3)} nats · uncertainty reduction ${(v.expected_uncertainty_reduction * 100).toFixed(1)}% · $${v.cost_usd} · ${v.days_required} days · cost-normalized VoI ${v.cost_normalized_voi.toFixed(4)}</div>
      <div class="fine">${v.rationale}</div>
    </div>
  `).join("");
}

function renderReport(inv) {
  const r = inv.report;
  $("report").innerHTML = `
    <p><b>${r.risk}</b> in ${r.geography} as of ${r.detection_time}.</p>
    <p>Discovered pathway: ${(r.discovered_pathway || []).join(" · ") || "insufficient structure"}</p>
    <p>Leading hypothesis: ${r.leading_hypothesis ? r.leading_hypothesis.statement : "none"}</p>
    <p>Next observation: ${r.next_best_observation ? r.next_best_observation.label : "n/a"}</p>
    <p>${r.low_regret_action}</p>
    <p class="muted">Would invalidate: ${(r.what_would_invalidate || []).join(" / ")}</p>
  `;
}

function reveal() {
  const ev = events.find((e) => e.id === $("event").value);
  if (!ev || !lastInv) return;
  const lead = lastInv.report.leading_hypothesis;
  $("outcome").classList.remove("hidden");
  $("outcome").innerHTML = `
    <h3>Historical outcome (held out until now)</h3>
    <p>Conventional visibility date: <b>${ev.conventional_visible_date}</b>. Cutoff used: <b>${ev.prediction_cutoff}</b>.</p>
    <p>${ev.documented_mechanism}</p>
    <p>Documented template: <b>${ev.documented_mechanism_template}</b>. jaadu.exe leader at cutoff: <b>${lead ? lead.template_id : "n/a"}</b>.</p>
    <p class="fine">This panel is intentionally unavailable during investigation so the replay cannot leak the answer.</p>
  `;
}

async function doPerturb() {
  const body = {
    region: $("region").value,
    as_of: $("asof").value,
    variable: $("pvar").value,
    delta_z: Number($("pdelta").value),
  };
  const res = await fetch("/api/perturb", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json();
  $("stress").textContent = JSON.stringify({ note: data.note, leading: (data.hypotheses || [])[0], pathway: data.pathway, n_abnormal: data.detection && data.detection.n_abnormal }, null, 2);
}

async function doAblate() {
  const drop = $("drop").value.split(",").map((s) => s.trim()).filter(Boolean);
  const res = await fetch("/api/ablate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ region: $("region").value, as_of: $("asof").value, drop_variables: drop }) });
  const data = await res.json();
  $("stress").textContent = JSON.stringify(data, null, 2);
}

async function renderBenchmark() {
  const b = await api("/api/benchmark");
  if (b.error) {
    $("benchmark").innerHTML = `<p class="muted">${b.error}</p>`;
    return;
  }
  $("benchmark").innerHTML = `<p>${b.summary.notes}</p>
    <p>Events ${b.summary.n_events} · detected at cutoff ${b.summary.detected} · hypothesis match ${b.summary.hypothesis_match} · mean false-alarm months ${b.summary.mean_false_alarms.toFixed(2)}</p>
    ${(b.events || []).map((e) => `<div class="ev"><b>${e.event_id}</b> alert=${e.multi_signal_alert_at_cutoff} lead_days=${e.lead_days_vs_conventional} leader=${e.leading_hypothesis} match=${e.hypothesis_matches_documented} FA=${e.false_alarms_in_negative_windows}</div>`).join("")}`;
}

boot();
