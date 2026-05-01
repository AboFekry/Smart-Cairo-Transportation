/* Cairo Smart Transportation Network — front-end */

const STATE = {
  network: null,
  nodesById: {},
  layers: {
    nodes: null,
    labels: null,
    existing: null,
    potential: null,
    metro: null,
    mst: null,
    route: null,
    emergency: null,
    raceDijkstra: null,
    raceAstar: null,
    ml: null,
  },
  ml: {trained: false, lastForecast: null},
  map: null,
};

// ---------------- Export / Download helper ----------------
/**
 * Trigger a browser download of `data` as a pretty-printed JSON file.
 * @param {object} data   - anything JSON-serialisable
 * @param {string} name   - filename without extension
 */
function downloadJSON(data, name = "cairo_result") {
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
  const url  = URL.createObjectURL(blob);
  const a    = Object.assign(document.createElement("a"), {href: url, download: `${name}.json`});
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Append a small "⬇ Download JSON" button to `container` (clears old one first). */
function addDownloadBtn(container, data, filename) {
  const old = container.querySelector(".dl-btn");
  if (old) old.remove();
  const btn = document.createElement("button");
  btn.className = "dl-btn";
  btn.textContent = "⬇ Download JSON";
  btn.style.cssText =
    "margin-top:10px;padding:4px 10px;font-size:11px;background:#2a4066;" +
    "color:#aac4f0;border:1px solid #3a5a8a;border-radius:4px;cursor:pointer;";
  btn.onclick = () => downloadJSON(data, filename);
  container.appendChild(btn);
}

// ---------------- Map setup ----------------
function initMap() {
  const map = L.map("map", {
    center: [30.05, 31.25],
    zoom: 11,
    minZoom: 9,
    maxZoom: 16,
    zoomControl: true,
    preferCanvas: true,
  });

  L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap &copy; CARTO",
      subdomains: "abcd",
    }
  ).addTo(map);

  STATE.map = map;
  for (const k of ["existing", "potential", "metro", "mst", "route", "emergency",
                   "raceDijkstra", "raceAstar", "ml", "nodes", "labels"]) {
    STATE.layers[k] = L.layerGroup().addTo(map);
  }
}

// ---------------- Data load ----------------
async function loadNetwork() {
  const res = await fetch("/api/network");
  const data = await res.json();
  STATE.network = data;
  STATE.nodesById = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
  populateNodeSelectors();
  drawNetwork();
  renderOverview();
  document.getElementById("map-status").textContent =
    `${data.nodes.length} nodes · ${data.edges.length} candidate edges`;
}

// ---------------- Drawing ----------------
function nodeColor(n) {
  if (n.medical) return "#ef4d68";
  if (n.critical) return "#e8b659";
  if (n.category === "facility") return "#4ec3c1";
  return "#8aa9ff";
}

function nodeRadius(n) {
  if (n.category === "facility") return 7;
  // scale by population
  const p = n.population || 0;
  return 6 + Math.min(8, Math.sqrt(p / 50000));
}

function drawNetwork() {
  STATE.layers.existing.clearLayers();
  STATE.layers.potential.clearLayers();
  STATE.layers.metro.clearLayers();
  STATE.layers.nodes.clearLayers();
  STATE.layers.labels.clearLayers();

  const period = document.getElementById("period-select").value;
  const showExisting = document.getElementById("show-existing").checked;
  const showPotential = document.getElementById("show-potential").checked;
  const showMetro = document.getElementById("show-metro").checked;
  const showLabels = document.getElementById("show-labels").checked;

  // --- edges
  for (const e of STATE.network.edges) {
    const a = STATE.nodesById[e.a];
    const b = STATE.nodesById[e.b];
    if (!a || !b) continue;
    const latlngs = [[a.y, a.x], [b.y, b.x]];

    if (e.kind === "existing") {
      if (!showExisting) continue;
      let color = "#5778c2";
      let weight = 2.5;
      if (period && e[period] != null && e.capacity) {
        const ratio = e[period] / e.capacity;
        // green -> yellow -> orange -> red
        if (ratio < 0.6) color = "#6dd58c";
        else if (ratio < 0.85) color = "#e8b659";
        else if (ratio < 1.05) color = "#f08a4b";
        else color = "#ef4d68";
        weight = 3;
      }
      const line = L.polyline(latlngs, {
        color, weight, opacity: 0.85,
      });
      line.bindPopup(
        `<b>${a.name} ↔ ${b.name}</b><br>` +
          `Distance: ${e.distance_km} km<br>` +
          `Capacity: ${e.capacity} veh/h<br>` +
          `Condition: ${e.condition}/10` +
          (e.morning != null
            ? `<br>Morning: ${e.morning} · Evening: ${e.evening}`
            : "")
      );
      STATE.layers.existing.addLayer(line);
    } else {
      if (!showPotential) continue;
      const line = L.polyline(latlngs, {
        color: "#8a9bc4",
        weight: 2,
        opacity: 0.7,
        dashArray: "6 6",
      });
      line.bindPopup(
        `<b>${a.name} ↔ ${b.name}</b> <i>(potential)</i><br>` +
          `Distance: ${e.distance_km} km<br>` +
          `Capacity: ${e.capacity} veh/h<br>` +
          `Construction: ${e.cost_million_egp} M EGP`
      );
      STATE.layers.potential.addLayer(line);
    }
  }

  // --- metro lines
  if (showMetro) {
    const metroColors = ["#e8b659", "#4ec3c1", "#ef4d68"];
    STATE.network.metro_lines.forEach((line, i) => {
      const pts = line.stations
        .map((id) => STATE.nodesById[id])
        .filter(Boolean)
        .map((n) => [n.y, n.x]);
      if (pts.length < 2) return;
      const poly = L.polyline(pts, {
        color: metroColors[i % metroColors.length],
        weight: 5,
        opacity: 0.55,
      });
      poly.bindPopup(`<b>${line.name}</b><br>Daily passengers: ${line.daily_passengers.toLocaleString()}`);
      STATE.layers.metro.addLayer(poly);
    });
  }

  // --- nodes
  for (const n of STATE.network.nodes) {
    const m = L.circleMarker([n.y, n.x], {
      radius: nodeRadius(n),
      color: "#0b1220",
      weight: 1.5,
      fillColor: nodeColor(n),
      fillOpacity: 0.95,
    });
    const popLine = n.population
      ? `<br>Population: ${n.population.toLocaleString()}`
      : "";
    m.bindPopup(
      `<b>${n.id} · ${n.name}</b><br>${n.type}${popLine}` +
        (n.critical ? "<br><i>Critical facility</i>" : "")
    );
    STATE.layers.nodes.addLayer(m);

    if (showLabels) {
      const lbl = L.marker([n.y, n.x], {
        icon: L.divIcon({
          className: "node-label",
          html: n.name,
          iconSize: null,
          iconAnchor: [-8, 8],
        }),
        interactive: false,
      });
      STATE.layers.labels.addLayer(lbl);
    }
  }
}

function clearOverlay(name) {
  STATE.layers[name].clearLayers();
}

// ---------------- Overview / selects ----------------
function renderOverview() {
  const stats = document.getElementById("overview-stats");
  const nodes = STATE.network.nodes;
  const edges = STATE.network.edges;
  const totalPop = nodes.reduce((s, n) => s + (n.population || 0), 0);
  const existing = edges.filter((e) => e.kind === "existing").length;
  const potential = edges.filter((e) => e.kind === "potential").length;
  const totalKm = edges
    .filter((e) => e.kind === "existing")
    .reduce((s, e) => s + e.distance_km, 0);
  stats.innerHTML = `
    <div class="stat"><div class="num">${nodes.length}</div><div class="lbl">Nodes</div></div>
    <div class="stat"><div class="num">${(totalPop / 1e6).toFixed(2)}M</div><div class="lbl">Total population</div></div>
    <div class="stat"><div class="num">${existing}</div><div class="lbl">Existing roads</div></div>
    <div class="stat"><div class="num">${potential}</div><div class="lbl">Potential roads</div></div>
    <div class="stat"><div class="num">${totalKm.toFixed(0)} km</div><div class="lbl">Total road length</div></div>
    <div class="stat"><div class="num">${STATE.network.metro_lines.length}</div><div class="lbl">Metro lines</div></div>
  `;
}

function populateNodeSelectors() {
  const groups = {
    "Neighborhoods": STATE.network.nodes.filter((n) => n.category === "neighborhood"),
    "Facilities": STATE.network.nodes.filter((n) => n.category === "facility"),
  };
  const selects = ["route-from", "route-to", "er-source", "er-target",
                   "race-from", "race-to"];
  selects.forEach((id) => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const keepFirst = id === "er-target";
    const firstOpt = keepFirst ? sel.options[0].outerHTML : "";
    sel.innerHTML = firstOpt;
    for (const [label, nodes] of Object.entries(groups)) {
      const og = document.createElement("optgroup");
      og.label = label;
      for (const n of nodes) {
        const o = document.createElement("option");
        o.value = n.id;
        o.textContent = `${n.id} · ${n.name}`;
        og.appendChild(o);
      }
      sel.appendChild(og);
    }
  });
  // sensible defaults
  document.getElementById("route-from").value = "1";
  document.getElementById("route-to").value = "13";
  document.getElementById("er-source").value = "7";
  document.getElementById("race-from").value = "1";
  document.getElementById("race-to").value = "13";
}

// ---------------- Path drawing ----------------
function pathLatLngs(path) {
  return path.map((id) => {
    const n = STATE.nodesById[id];
    return [n.y, n.x];
  });
}

function drawPath(layerName, path, options) {
  STATE.layers[layerName].clearLayers();
  if (!path || path.length < 2) return;
  const line = L.polyline(pathLatLngs(path), {
    color: options.color,
    weight: options.weight || 5,
    opacity: 0.95,
    lineCap: "round",
    dashArray: options.dashArray,
  });
  STATE.layers[layerName].addLayer(line);
  // start/end markers
  const start = STATE.nodesById[path[0]];
  const end = STATE.nodesById[path[path.length - 1]];
  STATE.layers[layerName].addLayer(
    L.circleMarker([start.y, start.x], {
      radius: 9, color: options.color, weight: 3, fillColor: "#0b1220", fillOpacity: 1,
    }).bindTooltip("Start: " + start.name, {permanent: false})
  );
  STATE.layers[layerName].addLayer(
    L.circleMarker([end.y, end.x], {
      radius: 9, color: options.color, weight: 3, fillColor: options.color, fillOpacity: 1,
    }).bindTooltip("End: " + end.name, {permanent: false})
  );
  STATE.map.fitBounds(L.polyline(pathLatLngs(path)).getBounds(), {padding: [60, 60]});
}

function pathToNames(path) {
  return path.map((id) => STATE.nodesById[id]?.name || id).join(" → ");
}

// ---------------- Tab switching ----------------
function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      document.getElementById("panel-" + tab.dataset.tab).classList.add("active");
    });
  });
}

// ---------------- MST ----------------
async function runMST() {
  const res = document.getElementById("mst-result");
  res.innerHTML = "Computing minimum spanning tree…";
  const params = new URLSearchParams({
    prioritize_population: document.getElementById("mst-prioritize").checked,
    ensure_critical_connectivity: document.getElementById("mst-critical").checked,
  });
  const data = await fetch("/api/mst?" + params).then((r) => r.json());

  // draw
  STATE.layers.mst.clearLayers();
  for (const e of data.edges) {
    const a = STATE.nodesById[e.a];
    const b = STATE.nodesById[e.b];
    if (!a || !b) continue;
    const isPotential = e.kind === "potential";
    const line = L.polyline([[a.y, a.x], [b.y, b.x]], {
      color: "#e8b659",
      weight: 4,
      opacity: 0.95,
      dashArray: isPotential ? "6 6" : null,
    });
    line.bindPopup(
      `<b>${a.name} ↔ ${b.name}</b><br>` +
        `Distance: ${e.distance.toFixed(1)} km<br>` +
        `Capacity: ${e.capacity} veh/h<br>` +
        (isPotential ? `Construction: ${e.cost_million_egp} M EGP` : `Condition: ${e.condition}/10`)
    );
    STATE.layers.mst.addLayer(line);
  }

  const isolatedNote = data.isolated_nodes && data.isolated_nodes.length
    ? `<p class="muted" style="margin-top:8px;font-size:11px;">
         Note: ${data.isolated_nodes.length} facilities have no road connections in the provided dataset:
         ${data.isolated_nodes.map((id) => STATE.nodesById[id]?.name || id).join(", ")}
       </p>`
    : "";
  res.innerHTML = `
    <div>
      <span class="pill">Edges: ${data.edge_count}</span>
      <span class="pill ${data.connected ? "green" : "red"}">${data.connected ? "Fully connected" : `${data.components} components`}</span>
    </div>
    <table>
      <tr><th>Nodes covered</th><td>${data.node_count - (data.isolated_nodes?.length || 0)} / ${data.node_count}</td></tr>
      <tr><th>Total length</th><td>${data.total_distance_km} km</td></tr>
      <tr><th>New construction</th><td>${data.total_construction_cost_million_egp} M EGP</td></tr>
      <tr><th>Compute time</th><td>${data.elapsed_ms} ms</td></tr>
      <tr><th>Complexity</th><td>${data.complexity}</td></tr>
    </table>
    ${isolatedNote}
  `;
  addDownloadBtn(res, data, "mst_result");
}

// ---------------- Routing ----------------
async function runRoute() {
  const src = document.getElementById("route-from").value;
  const dst = document.getElementById("route-to").value;
  const period = document.getElementById("route-period").value;
  if (src === dst) {
    document.getElementById("route-result").innerHTML = "<i>Choose two different nodes.</i>";
    return;
  }
  document.getElementById("route-result").innerHTML = "Computing routes…";
  const data = await fetch(
    `/api/route/compare?source=${src}&target=${dst}&period=${period}`
  ).then((r) => r.json());

  // Draw the A* time-aware route as the primary.
  drawPath("route", data.astar_time.path, {color: "#4ec3c1", weight: 5});

  const dijkstraDist = data.dijkstra_distance;
  const dijkstraTime = data.dijkstra_time;
  const astarTime = data.astar_time;

  document.getElementById("route-result").innerHTML = `
    <div><strong>${pathToNames(astarTime.path)}</strong></div>
    <table>
      <tr><th>Algorithm</th><th>Cost</th><th>Nodes expanded</th><th>Time</th></tr>
      <tr><td>Dijkstra (km)</td><td>${dijkstraDist.cost ?? "–"} km</td><td>${dijkstraDist.expanded ?? "–"}</td><td>${dijkstraDist.elapsed_ms ?? "–"} ms</td></tr>
      <tr><td>Dijkstra (${period})</td><td>${dijkstraTime.cost ?? "–"} min</td><td>${dijkstraTime.expanded ?? "–"}</td><td>${dijkstraTime.elapsed_ms ?? "–"} ms</td></tr>
      <tr><td>A* (${period})</td><td>${astarTime.cost ?? "–"} min</td><td>${astarTime.expanded ?? "–"}</td><td>${astarTime.elapsed_ms ?? "–"} ms</td></tr>
    </table>
    <p class="muted" style="margin-top:8px;font-size:11px;">
      A* uses a Haversine heuristic — typically expands fewer nodes than Dijkstra for the same answer.
    </p>
  `;
  addDownloadBtn(document.getElementById("route-result"), data, "routing_result");
}

function clearRoute() {
  STATE.layers.route.clearLayers();
  STATE.layers.raceDijkstra.clearLayers();
  STATE.layers.raceAstar.clearLayers();
  document.getElementById("route-result").innerHTML = "";
}

// ---------------- Algorithm Race (side-by-side visualizer) ----------------
const RACE = {running: false, abort: false};

function clearRace() {
  RACE.abort = true;
  STATE.layers.raceDijkstra.clearLayers();
  STATE.layers.raceAstar.clearLayers();
  document.getElementById("race-board").innerHTML = "";
}

function renderRaceBoard(d, a) {
  document.getElementById("race-board").innerHTML = `
    <div class="racer dijkstra" id="racer-d">
      <div class="head">
        <div><span class="name">Dijkstra</span> <span class="muted">— uniform-cost</span>
          <span class="winner-badge" id="badge-d" style="display:none">Winner</span>
        </div>
        <div><b id="d-count">0</b> / ${d.visited_order.length}</div>
      </div>
      <div class="progress-track"><div class="progress-fill" id="d-fill"></div></div>
      <div class="stats">
        <span>Final cost: <b>${d.cost ?? "–"} ${d.unit || ""}</b></span>
        <span>Total expanded: <b>${d.visited_order.length}</b></span>
        <span>Server time: <b>${d.elapsed_ms} ms</b></span>
      </div>
    </div>
    <div class="racer astar" id="racer-a">
      <div class="head">
        <div><span class="name">A*</span> <span class="muted">— Haversine heuristic</span>
          <span class="winner-badge" id="badge-a" style="display:none">Winner</span>
        </div>
        <div><b id="a-count">0</b> / ${a.visited_order.length}</div>
      </div>
      <div class="progress-track"><div class="progress-fill" id="a-fill"></div></div>
      <div class="stats">
        <span>Final cost: <b>${a.cost ?? "–"} ${a.unit || ""}</b></span>
        <span>Total expanded: <b>${a.visited_order.length}</b></span>
        <span>Server time: <b>${a.elapsed_ms} ms</b></span>
      </div>
    </div>
    <div class="race-summary" id="race-summary">
      Watching the search frontiers expand. Pulses = node expansions.
    </div>
  `;
}

async function runRace() {
  if (RACE.running) return;
  const src = document.getElementById("race-from").value;
  const dst = document.getElementById("race-to").value;
  const period = document.getElementById("race-period").value;
  const speed = +document.getElementById("race-speed").value;
  if (src === dst) {
    document.getElementById("race-board").innerHTML =
      "<i>Choose two different nodes.</i>";
    return;
  }
  document.getElementById("race-board").innerHTML = "Loading race…";

  const data = await fetch(
    `/api/route/race?source=${src}&target=${dst}&period=${period}`
  ).then((r) => r.json());

  STATE.layers.route.clearLayers();
  STATE.layers.raceDijkstra.clearLayers();
  STATE.layers.raceAstar.clearLayers();

  // Frame the map to the relevant area (start + end + neighborhood).
  try {
    const s = STATE.nodesById[src];
    const e = STATE.nodesById[dst];
    if (s && e) {
      STATE.map.fitBounds(L.latLngBounds([[s.y, s.x], [e.y, e.x]]),
        {padding: [80, 80]});
    }
  } catch (_) { /* ignore */ }

  renderRaceBoard(data.dijkstra, data.astar);

  RACE.running = true;
  RACE.abort = false;

  const winner = {algo: null};
  const stepMs = speed;

  const dPromise = animateExpansion({
    order: data.dijkstra.visited_order,
    prev: data.dijkstra.prev,
    layer: "raceDijkstra",
    color: "#f08a4b",
    counterId: "d-count",
    fillId: "d-fill",
    stepMs,
    onFirstFinish: () => {
      if (!winner.algo) winner.algo = "dijkstra";
    },
  });
  const aPromise = animateExpansion({
    order: data.astar.visited_order,
    prev: data.astar.prev,
    layer: "raceAstar",
    color: "#4ec3c1",
    counterId: "a-count",
    fillId: "a-fill",
    stepMs,
    onFirstFinish: () => {
      if (!winner.algo) winner.algo = "astar";
    },
  });

  await Promise.all([dPromise, aPromise]);

  if (RACE.abort) {
    RACE.running = false;
    return;
  }

  // Draw final paths
  if (data.astar.path && data.astar.path.length >= 2) {
    STATE.layers.raceAstar.addLayer(L.polyline(pathLatLngs(data.astar.path), {
      color: "#4ec3c1", weight: 4, opacity: 0.95,
    }));
  }
  if (data.dijkstra.path && data.dijkstra.path.length >= 2) {
    STATE.layers.raceDijkstra.addLayer(L.polyline(pathLatLngs(data.dijkstra.path), {
      color: "#f08a4b", weight: 4, opacity: 0.85, dashArray: "5 7",
    }));
  }

  // Highlight winner card and write summary
  const dN = data.dijkstra.visited_order.length;
  const aN = data.astar.visited_order.length;
  const winAlgo = winner.algo || (aN <= dN ? "astar" : "dijkstra");
  if (winAlgo === "astar") {
    document.getElementById("racer-a").classList.add("winner");
    document.getElementById("badge-a").style.display = "inline-block";
  } else {
    document.getElementById("racer-d").classList.add("winner");
    document.getElementById("badge-d").style.display = "inline-block";
  }
  const saved = dN - aN;
  const pct = dN > 0 ? ((saved / dN) * 100).toFixed(0) : 0;
  const sameCost =
    data.dijkstra.cost != null &&
    data.astar.cost != null &&
    Math.abs(data.dijkstra.cost - data.astar.cost) < 0.01;
  document.getElementById("race-summary").innerHTML = `
    <strong>${winAlgo === "astar" ? "A*" : "Dijkstra"} reached the goal first.</strong>
    A* expanded <b>${aN}</b> nodes vs Dijkstra's <b>${dN}</b>
    (${saved >= 0 ? saved : 0} fewer, ${Math.max(0, +pct)}% saved).
    ${sameCost
      ? "Both algorithms found a path of equal cost — A* is just smarter about <em>which</em> nodes to look at."
      : "Costs differ slightly because A* targets the goal directly while Dijkstra explores all directions."}
  `;
  RACE.running = false;
}

function animateExpansion({order, prev, layer, color, counterId, fillId, stepMs, onFirstFinish}) {
  return new Promise((resolve) => {
    if (!order || order.length === 0) { resolve(); return; }
    const counter = document.getElementById(counterId);
    const fill = document.getElementById(fillId);
    let i = 0;
    const total = order.length;
    const step = () => {
      if (RACE.abort) { resolve(); return; }
      if (i >= total) {
        if (onFirstFinish) onFirstFinish();
        resolve();
        return;
      }
      const id = order[i];
      const n = STATE.nodesById[id];
      if (n) {
        if (prev && prev[id]) {
          const p = STATE.nodesById[prev[id]];
          if (p) {
            const edgeLine = L.polyline([[p.y, p.x], [n.y, n.x]], {
              color: color,
              weight: 2,
              opacity: 0.6,
              dashArray: "4 4"
            });
            STATE.layers[layer].addLayer(edgeLine);
          }
        }
        const dot = L.circleMarker([n.y, n.x], {
          radius: 4,
          color: color,
          weight: 2,
          fillColor: color,
          fillOpacity: 0.45,
        });
        STATE.layers[layer].addLayer(dot);
        let r = 4;
        const pulse = setInterval(() => {
          r += 1.4;
          dot.setRadius(r);
          if (r > 12) {
            clearInterval(pulse);
            dot.setRadius(5);
            dot.setStyle({fillOpacity: 0.9});
          }
        }, 40);
      }
      i += 1;
      if (counter) counter.textContent = i;
      if (fill) fill.style.width = ((i / total) * 100) + "%";
      setTimeout(step, stepMs);
    };
    step();
  });
}

// ---------------- ML Forecast ----------------
async function trainML() {
  const out = document.getElementById("ml-metrics");
  out.innerHTML = "Training Random Forest…";
  const data = await fetch("/api/ml/train?force=true").then((r) => r.json());
  STATE.ml.trained = true;
  const fi = data.feature_importances
    .map((f) => `<tr><td>${f.feature}</td><td>${(f.importance * 100).toFixed(1)}%</td></tr>`)
    .join("");
  const trainTimeRow = data.train_time_ms != null
    ? `<tr><th>Train time</th><td>${data.train_time_ms} ms</td></tr>`
    : (data.train_ms != null
        ? `<tr><th>Train time</th><td>${data.train_ms} ms</td></tr>`
        : "");
  const sourceRow = data.loaded_from_disk
    ? `<tr><th>Source</th><td>Loaded from disk · trained ${data.trained_at || "—"}</td></tr>`
    : `<tr><th>Source</th><td>Trained in-process</td></tr>`;
  const rmseRow = data.test_rmse_vehicles_per_hour != null
    ? `<tr><th>Test RMSE</th><td>${data.test_rmse_vehicles_per_hour} veh/h</td></tr>`
    : "";
  out.innerHTML = `
    <table>
      <tr><th>Model</th><td>${data.model}${data.n_estimators ? ` (${data.n_estimators} trees, depth ${data.max_depth})` : ""}</td></tr>
      ${sourceRow}
      <tr><th>Samples</th><td>${data.samples_total} (train ${data.samples_train} / test ${data.samples_test})</td></tr>
      <tr><th>Test MAE</th><td>${data.test_mae_vehicles_per_hour} veh/h</td></tr>
      ${rmseRow}
      <tr><th>Test R²</th><td>${data.test_r2}</td></tr>
      ${trainTimeRow}
    </table>
    <h3 style="margin-top:10px">Feature importances</h3>
    <table>
      <tr><th>Feature</th><th>Weight</th></tr>
      ${fi}
    </table>
    <p class="muted" style="margin-top:8px;font-size:11px;">
      Tip: retrain offline with <code>python train_model.py --data data/traffic_data.csv</code>
      to swap in your own dataset.
    </p>
  `;
  addDownloadBtn(out, data, "ml_model_metrics");
}

async function predictML() {
  const hour = +document.getElementById("ml-hour").value;
  const out = document.getElementById("ml-result");
  out.innerHTML = "Forecasting…";
  const data = await fetch(`/api/ml/predict?hour=${hour}`).then((r) => r.json());
  if (data.error) {
    out.innerHTML = `<i>${data.error}</i>`;
    return;
  }
  STATE.ml.lastForecast = data;
  recolorMapByForecast(data.roads);

  const top = data.top_congested
    .map((r) => {
      const a = STATE.nodesById[r.a]?.name || r.a;
      const b = STATE.nodesById[r.b]?.name || r.b;
      const ratioColor = r.vc_ratio > 1.0 ? "red"
                       : r.vc_ratio > 0.85 ? "" : "green";
      return `<tr><td>${a} ↔ ${b}</td><td>${r.predicted_vehicles_per_hour}</td>
              <td><span class="pill ${ratioColor}">V/C ${r.vc_ratio}</span></td></tr>`;
    })
    .join("");
  out.innerHTML = `
    <div><strong>Predicted congestion at ${String(hour).padStart(2, "0")}:00</strong></div>
    <table>
      <tr><th>Road</th><th>Veh/h</th><th>V/C</th></tr>
      ${top}
    </table>
    <p class="muted" style="margin-top:8px;font-size:11px;">
      Roads on the map are now colored by predicted V/C ratio for the chosen hour.
    </p>
  `;
  addDownloadBtn(out, data, `ml_forecast_h${String(hour).padStart(2,"0")}`);
}

function recolorMapByForecast(roads) {
  STATE.layers.ml.clearLayers();
  // hide existing-road overlay so the ML layer reads cleanly
  STATE.layers.existing.clearLayers();
  for (const r of roads) {
    const a = STATE.nodesById[r.a];
    const b = STATE.nodesById[r.b];
    if (!a || !b) continue;
    const ratio = r.vc_ratio;
    let color;
    if (ratio < 0.6) color = "#6dd58c";
    else if (ratio < 0.85) color = "#e8b659";
    else if (ratio < 1.05) color = "#f08a4b";
    else color = "#ef4d68";
    const line = L.polyline([[a.y, a.x], [b.y, b.x]], {
      color, weight: 3.5, opacity: 0.9,
      dashArray: r.is_existing ? null : "5 6",
    });
    line.bindPopup(
      `<b>${a.name} ↔ ${b.name}</b><br>` +
      `Predicted: ${r.predicted_vehicles_per_hour} veh/h<br>` +
      `Capacity: ${r.capacity}<br>` +
      `V/C: ${r.vc_ratio}`
    );
    STATE.layers.ml.addLayer(line);
  }
}

async function predictCustomML() {
  const hour = +document.getElementById("ml-hour").value;
  const dist = +document.getElementById("ml-custom-dist").value;
  const cap = +document.getElementById("ml-custom-cap").value;
  const pop = +document.getElementById("ml-custom-pop").value;
  const existing = document.getElementById("ml-custom-existing").checked ? 1 : 0;
  
  const out = document.getElementById("ml-custom-result");
  out.innerHTML = "Predicting...";
  
  const params = new URLSearchParams({
    hour: hour,
    distance: dist,
    capacity: cap,
    pop: pop,
    existing: existing
  });
  
  const data = await fetch("/api/ml/predict_custom?" + params).then((r) => r.json());
  
  if (data.error) {
    out.innerHTML = `<i>${data.error}</i>`;
    return;
  }
  
  const ratioColor = data.vc_ratio > 1.0 ? "red" : data.vc_ratio > 0.85 ? "" : "green";
  
  out.innerHTML = `
    <table>
      <tr><th>Predicted Volume</th><td>${data.predicted_vehicles_per_hour} veh/h</td></tr>
      <tr><th>V/C Ratio</th><td><span class="pill ${ratioColor}">${data.vc_ratio}</span></td></tr>
    </table>
  `;
}

// ---------------- Emergency ----------------
async function runEmergency() {
  const src = document.getElementById("er-source").value;
  const dst = document.getElementById("er-target").value;
  const period = document.getElementById("er-period").value;
  document.getElementById("er-result").innerHTML = "Dispatching…";
  const params = new URLSearchParams({source: src, period});
  if (dst) params.set("target", dst);
  const data = await fetch("/api/emergency?" + params).then((r) => r.json());
  if (!data.path || data.path.length < 2) {
    document.getElementById("er-result").innerHTML = "<i>No route found.</i>";
    return;
  }
  drawPath("emergency", data.path, {color: "#ef4d68", weight: 6});
  const facilityName = data.facility_id
    ? STATE.nodesById[data.facility_id]?.name
    : null;
  const headerExtra = facilityName
    ? `<div><strong>Nearest hospital: ${facilityName}</strong></div>`
    : "";
  const noteHtml = data.note
    ? `<p class="muted" style="margin-top:8px;font-size:11px;">${data.note}</p>`
    : "";
  document.getElementById("er-result").innerHTML = `
    ${headerExtra}
    <div>${pathToNames(data.path)}</div>
    <table>
      <tr><th>Emergency time</th><td>${data.emergency_minutes ?? "–"} min</td></tr>
      <tr><th>Normal time</th><td>${data.normal_minutes ?? "–"} min</td></tr>
      <tr><th>Time saved</th><td><span class="pill green">${data.saved_minutes ?? 0} min</span></td></tr>
      <tr><th>Signals preempted</th><td>${data.preempted_count}</td></tr>
    </table>
    ${noteHtml}
  `;
  addDownloadBtn(document.getElementById("er-result"), data, "emergency_result");
}

// ---------------- Transit ----------------
async function runTransit() {
  const v = document.getElementById("transit-vehicles").value;
  document.getElementById("transit-result").innerHTML = "Optimizing schedule…";
  const data = await fetch("/api/transit/schedule?total_vehicles=" + v).then((r) => r.json());
  let rows = data.plan
    .filter((p) => p.vehicles_assigned > 0)
    .sort((a, b) => b.estimated_passengers - a.estimated_passengers)
    .map(
      (p) =>
        `<tr><td>${p.kind === "metro" ? "🚇" : "🚌"} ${p.name}</td><td>${p.vehicles_assigned}</td><td>${p.estimated_passengers.toLocaleString()}</td></tr>`
    )
    .join("");
  document.getElementById("transit-result").innerHTML = `
    <div>
      <span class="pill">${data.vehicles_used}/${data.total_vehicles} vehicles</span>
      <span class="pill green">${data.total_estimated_passengers.toLocaleString()} passengers/day</span>
    </div>
    <table>
      <tr><th>Line</th><th>Vehicles</th><th>Passengers</th></tr>
      ${rows}
    </table>
    <p class="muted" style="margin-top:8px;font-size:11px;">${data.complexity} · solved in ${data.elapsed_ms} ms</p>
  `;
  addDownloadBtn(document.getElementById("transit-result"), data, "transit_schedule");
}

// ---------------- Maintenance ----------------
async function runMaintenance() {
  const b = document.getElementById("maint-budget").value;
  document.getElementById("maint-result").innerHTML = "Optimizing budget…";
  const data = await fetch("/api/maintenance?budget=" + b).then((r) => r.json());
  let rows = data.chosen
    .map((c) => {
      const a = STATE.nodesById[c.a]?.name || c.a;
      const bn = STATE.nodesById[c.b]?.name || c.b;
      return `<tr><td>${a} ↔ ${bn}</td><td>${c.distance.toFixed(1)} km</td><td>${c.condition}/10</td><td>${c.cost} M</td></tr>`;
    })
    .join("");
  document.getElementById("maint-result").innerHTML = `
    <div>
      <span class="pill">${data.chosen.length} roads</span>
      <span class="pill green">${data.total_cost_million_egp} / ${data.budget_million_egp} M EGP</span>
    </div>
    <table>
      <tr><th>Road</th><th>Length</th><th>Condition</th><th>Cost</th></tr>
      ${rows}
    </table>
    <p class="muted" style="margin-top:8px;font-size:11px;">${data.complexity} · solved in ${data.elapsed_ms} ms</p>
  `;
  addDownloadBtn(document.getElementById("maint-result"), data, "maintenance_plan");
}

// ---------------- Signals ----------------
async function runSignals() {
  const period = document.getElementById("sig-period").value;
  document.getElementById("sig-result").innerHTML = "Optimizing signals…";
  const data = await fetch("/api/signals?period=" + period).then((r) => r.json());
  const top = data.intersections.slice(0, 8);
  const rows = top
    .map((i) => {
      const name = STATE.nodesById[i.intersection]?.name || i.intersection;
      const greens = i.allocations
        .map((a) => `${STATE.nodesById[a.approach_from]?.name || a.approach_from}: ${a.green_seconds}s`)
        .join("<br>");
      return `<tr><td><b>${name}</b><br><span style="color:var(--muted);font-size:11px">${i.total_flow_vph} veh/h total</span></td><td>${greens}</td></tr>`;
    })
    .join("");
  document.getElementById("sig-result").innerHTML = `
    <div><span class="pill">${data.intersections.length} intersections</span></div>
    <table>
      <tr><th>Intersection</th><th>Green allocation</th></tr>
      ${rows}
    </table>
    <p class="muted" style="margin-top:8px;font-size:11px;">${data.complexity}</p>
  `;
  addDownloadBtn(document.getElementById("sig-result"), data, "signal_optimization");
}

// ---------------- Wiring ----------------
function bindControls() {
  ["show-existing", "show-potential", "show-metro", "show-labels", "period-select"].forEach(
    (id) => document.getElementById(id).addEventListener("change", drawNetwork)
  );
  document.getElementById("mst-run").addEventListener("click", runMST);
  document.getElementById("route-run").addEventListener("click", runRoute);
  document.getElementById("route-clear").addEventListener("click", clearRoute);
  document.getElementById("er-run").addEventListener("click", runEmergency);
  document.getElementById("transit-run").addEventListener("click", runTransit);
  document.getElementById("maint-run").addEventListener("click", runMaintenance);
  document.getElementById("sig-run").addEventListener("click", runSignals);
  document.getElementById("race-run").addEventListener("click", runRace);
  document.getElementById("race-clear").addEventListener("click", clearRace);
  const speedSlider = document.getElementById("race-speed");
  speedSlider.addEventListener("input", () => {
    const v = +speedSlider.value;
    const label = v < 120 ? "Fast" : v < 260 ? "Normal" : v < 380 ? "Slow" : "Very slow";
    document.getElementById("race-speed-label").textContent = label;
  });
  document.getElementById("ml-train").addEventListener("click", trainML);
  document.getElementById("ml-predict").addEventListener("click", predictML);
  document.getElementById("ml-custom-predict").addEventListener("click", predictCustomML);
  const hourSlider = document.getElementById("ml-hour");
  hourSlider.addEventListener("input", () => {
    document.getElementById("ml-hour-label").textContent =
      `${String(hourSlider.value).padStart(2, "0")}:00`;
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  initMap();
  setupTabs();
  await loadNetwork();
  bindControls();
});
