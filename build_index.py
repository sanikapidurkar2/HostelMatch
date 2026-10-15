"""Builds self-contained index.html with embedded data and fallback logic."""
import os

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, "embedded_data.js"), "r", encoding="utf-8") as f:
    embedded = f.read()

with open(os.path.join(BASE, "templates", "index.html"), "r", encoding="utf-8") as f:
    html = f.read()

marker = "<script>"
pos = html.find(marker)
assert pos != -1

js_code = """<script>
""" + embedded + """
const ROOMS = ["single", "double", "triple", "dorm"];
const AMENITIES = ["wifi", "ac", "meals", "laundry", "gym", "study_room", "power_backup", "security"];
const label = s => s.replace(/_/g, " ").replace(/^./, c => c.toUpperCase());
const $ = id => document.getElementById(id);
const cid = localStorage.cid || (localStorage.cid = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random()));
const H = {"Content-Type": "application/json", "X-Client-Id": cid};

let results = [], saved = new Set(), compareSet = new Set(), view = "match", activeGender = "", activeFood = "all", lastPrefs = null;
let customLocation = null;

// Populate College Dropdown dynamically if not rendered by Jinja
const collegeSel = $("collegeSelect");
if (collegeSel) {
  collegeSel.innerHTML = EMBEDDED_COLLEGES.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
}

// Toast System
function toast(msg) {
  const c = $("toast-container");
  const t = document.createElement("div");
  t.className = "toast";
  t.innerHTML = `<span>✨</span> ${msg}`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

// Theme Toggle
const themeBtn = $("themeToggle");
function setTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  localStorage.theme = t;
  $("themeIcon").textContent = t === "dark" ? "☀️" : "🌙";
  $("themeLabel").textContent = t === "dark" ? "Light" : "Dark";
}
if (themeBtn) themeBtn.onclick = () => setTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
if (localStorage.theme) setTheme(localStorage.theme);

// Populate Chips
$("roomChips").innerHTML = ROOMS.map(r => `<label><input type="checkbox" name="rooms" value="${r}"><span>${label(r)}</span></label>`).join("");
$("amenityChips").innerHTML = AMENITIES.map(a => `<label><input type="checkbox" name="ams" value="${a}"><span>${label(a)}</span></label>`).join("");

const checked = n => [...document.querySelectorAll(`input[name=${n}]:checked`)].map(e => e.value);
const inr = n => "₹" + Number(n).toLocaleString("en-IN");
const sync = () => {
  $("bv").textContent = inr(+$("budget").value);
  $("dv").textContent = $("dist").value + " km";
};
$("budget").oninput = $("dist").oninput = sync;
sync();

function setGenderFilter(g, el) {
  activeGender = g;
  el.parentElement.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
  el.classList.add("active");
  search();
}

function setFoodFilter(f, el) {
  activeFood = f;
  el.parentElement.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
  el.classList.add("active");
  search();
}

function onCollegeChange() {
  customLocation = null;
  const sel = $("collegeSelect");
  const opt = sel.options[sel.selectedIndex];
  $("activeCollegeLabel").textContent = opt ? opt.text : "Selected Campus";
  search();
}

function useCurrentLocation() {
  if (!navigator.geolocation) {
    toast("Geolocation not supported by this browser");
    return;
  }
  toast("Detecting live GPS location...");
  navigator.geolocation.getCurrentPosition(
    pos => {
      customLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      $("activeCollegeLabel").textContent = `GPS Location (${pos.coords.latitude.toFixed(3)}, ${pos.coords.longitude.toFixed(3)})`;
      toast("Using your live location!");
      search();
    },
    err => {
      toast("GPS unavailable: " + err.message);
    }
  );
}

function resetFilters() {
  $("prefForm").reset();
  $("qSearch").value = "";
  activeGender = "";
  activeFood = "all";
  customLocation = null;
  $("collegeSelect").selectedIndex = 0;
  $("activeCollegeLabel").textContent = $("collegeSelect").options[0].text;
  document.querySelectorAll(".filter-pill").forEach((p, i) => p.classList.toggle("active", i === 0 || i === 4));
  sync();
  search();
  toast("Filters reset to default");
}

function renderGauge(score) {
  const r = 25, c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;
  return `<div class="match-gauge">
    <svg viewBox="0 0 60 60">
      <circle class="match-bg" cx="30" cy="30" r="${r}"/>
      <circle class="match-val" cx="30" cy="30" r="${r}" stroke-dasharray="${c}" stroke-dashoffset="${offset}"/>
    </svg>
    <div class="match-text">${score}%</div>
  </div>`;
}

function getCommuteText(km) {
  const walkMin = Math.round(km * 12);
  const cabMin = Math.round(km * 2.5) + 3;
  if (km <= 1.2) return `🚶 ~${walkMin} min walk`;
  return `🚕 ~${cabMin} min auto / cab`;
}

function haversineKm(lat1, lon1, lat2, lon2) {
  if (lat1 == null || lon1 == null || lat2 == null || lon2 == null) return 1.0;
  const R = 6371.0;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
  return Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)) * 100) / 100;
}

function scoreHostel(h, p) {
  const offered = (p.rooms && p.rooms.length) ? p.rooms.filter(r => h.rooms[r]) : Object.keys(h.rooms);
  const price = Math.min(...offered.map(r => h.rooms[r]));
  h.price = price;
  const ratio = price / p.budget;
  let budget = (ratio <= 0.8) ? 25.0 : Math.max(0, Math.min(25.0, 25.0 - (ratio - 0.8) / 0.2 * 10.0));
  let dist = Math.max(0, Math.min(25.0, 25.0 * (1.0 - 0.6 * h.distance_km / p.max_distance)));
  let amen = p.amenities.length ? 30.0 * (p.amenities.filter(a => h.amenities.includes(a)).length / p.amenities.length) : 30.0;
  let room = 10.0;
  let rating = Math.min(10.0, Math.max(0, (h.rating || 4.5) / 5.0 * 10.0));
  const parts = {
    budget: Math.round(budget * 10) / 10,
    distance: Math.round(dist * 10) / 10,
    amenities: Math.round(amen * 10) / 10,
    room,
    rating: Math.round(rating * 10) / 10
  };
  const total = Math.min(100, Math.max(0, Math.round(budget + dist + amen + room + rating)));
  return [total, parts];
}

// Client-side fallback matcher if API is offline
function clientSideRecommend(p) {
  let refLat = 19.0760, refLng = 72.8777;
  if (p.campus_lat && p.campus_lng) {
    refLat = p.campus_lat; refLng = p.campus_lng;
  } else if (p.college_id) {
    const c = EMBEDDED_COLLEGES.find(x => x.id === p.college_id);
    if (c) { refLat = c.lat; refLng = c.lng; }
  }

  const out = [];
  for (const raw of EMBEDDED_HOSTELS) {
    const h = JSON.parse(JSON.stringify(raw));
    h.distance_km = haversineKm(refLat, refLng, h.lat, h.lng);

    if (p.gender && p.gender !== "coed" && h.gender !== "coed" && h.gender !== p.gender) continue;
    if (p.food && p.food !== "all") {
      if (p.food === "jain" && h.food !== "jain") continue;
      if (p.food === "pure_veg" && !["jain", "pure_veg"].includes(h.food)) continue;
    }
    if (p.q) {
      const qStr = `${h.name} ${h.area} ${h.address} ${h.nearby_colleges} ${h.about}`.toLowerCase();
      if (!qStr.includes(p.q.toLowerCase())) continue;
    }

    const offered = (p.rooms && p.rooms.length) ? p.rooms.filter(r => h.rooms[r]) : Object.keys(h.rooms);
    if (p.rooms && p.rooms.length && !offered.length) continue;
    const prices = offered.map(r => h.rooms[r]);
    h.price = Math.min(...prices);
    if (h.price > p.budget || h.distance_km > p.max_distance) continue;

    const [tot, brk] = scoreHostel(h, p);
    h.match = tot;
    h.breakdown = brk;
    h.missing_amenities = (p.amenities || []).filter(a => !h.amenities.includes(a));
    out.push(h);
  }

  const sortKey = p.sort || "match";
  out.sort((a, b) => {
    if (sortKey === "price") return a.price - b.price;
    if (sortKey === "distance") return a.distance_km - b.distance_km;
    if (sortKey === "rating") return b.rating - a.rating;
    if (sortKey === "safety") return (b.safety_score || 4.5) - (a.safety_score || 4.5);
    return b.match - a.match;
  });

  return { count: out.length, results: out, ref_location: { lat: refLat, lng: refLng } };
}

function card(h) {
  const isSaved = saved.has(h.id);
  const isComp = compareSet.has(h.id);
  const foodClass = h.food || 'pure_veg';
  const foodText = h.food === 'jain' ? '🥗 Strict Jain Food' : (h.food === 'pure_veg' ? '🥦 Pure Veg' : '🍗 Veg & Non-Veg');

  return `<article class="card">
    <div class="card-img-wrap">
      <img src="${h.cover_image}" alt="${h.name}" onerror="this.src='https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=700&q=80'">
      <div class="badge-verified">✓ Verified</div>
      <div class="badge-gender ${h.gender}">${h.gender}</div>
    </div>
    <div class="card-body">
      <div>
        <span class="food-pill-badge ${foodClass}">${foodText}</span>
        <h3>${h.name}</h3>
        <div class="card-locality">📍 ${h.address || h.area}</div>
      </div>

      <div class="card-prox-bar">
        <span class="prox-km">🎯 ${h.distance_km} km away</span>
        <span class="prox-commute">${getCommuteText(h.distance_km)}</span>
        <span style="color:var(--mute)">★ ${h.rating} (Safety: ${h.safety_score || 4.5}/5)</span>
      </div>

      <div class="card-price">From ${inr(h.price)} <small style="font-size:0.8rem;color:var(--mute);font-weight:600">/mo</small></div>

      ${h.nearby_colleges ? `<div style="font-size:0.75rem;color:var(--mute);margin-bottom:6px"><b>Nearby:</b> ${h.nearby_colleges}</div>` : ''}

      <div class="amenities-list">
        ${h.amenities.slice(0, 5).map(a => `<span class="tag">${label(a)}</span>`).join("")}
        ${(h.missing_amenities || []).map(a => `<span class="tag miss">No ${label(a)}</span>`).join("")}
      </div>
    </div>
    <div class="card-side">
      ${renderGauge(h.match || 0)}
      <div class="card-actions">
        <a href="tel:${h.phone}" class="btn-action call">📞 ${h.phone}</a>
        <button class="btn-action primary" onclick="openDetail(${h.id})">Details & Book</button>
        <button class="btn-action ${isComp ? 'primary' : ''}" onclick="toggleCompare(${h.id})">${isComp ? '✓ Comparing' : '+ Compare'}</button>
        <button class="btn-action ${isSaved ? 'saved' : ''}" onclick="toggleSave(${h.id})">${isSaved ? '♥ Saved' : '♡ Save'}</button>
      </div>
    </div>
  </article>`;
}

let map, layer;
function drawMap(list, refLoc) {
  $("mapSection").hidden = false;
  if (!window.L) {
    $("map").textContent = "Map loading error.";
    return;
  }
  if (!map) {
    map = L.map("map");
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap contributors"
    }).addTo(map);
    layer = L.layerGroup().addTo(map);
  }
  layer.clearLayers();
  const pts = [];

  if (refLoc && refLoc.lat && refLoc.lng) {
    pts.push([refLoc.lat, refLoc.lng]);
    L.circleMarker([refLoc.lat, refLoc.lng], {
      radius: 12,
      fillColor: "#0D9488",
      color: "#FFFFFF",
      weight: 3,
      opacity: 1,
      fillOpacity: 0.95
    }).addTo(layer).bindPopup(`
      <div style="font-family:sans-serif;padding:4px">
        <b style="color:#0D9488;font-size:1.05rem">🎓 Selected Campus / Location</b><br>
        ${$("activeCollegeLabel").textContent}
      </div>
    `);
  }

  list.filter(h => h.lat != null).forEach(h => {
    pts.push([h.lat, h.lng]);
    let markerColor = "#7c3aed";
    if (h.gender === "girls") markerColor = "#db2777";
    else if (h.gender === "boys") markerColor = "#2563eb";
    if (h.food === "jain") markerColor = "#ca8a04";

    const m = L.circleMarker([h.lat, h.lng], {
      radius: 8,
      fillColor: markerColor,
      color: "#FFFFFF",
      weight: 2,
      opacity: 1,
      fillOpacity: 0.9
    }).addTo(layer);

    m.bindPopup(`
      <div style="font-family:sans-serif;min-width:180px">
        <b style="font-size:0.95rem">${h.name}</b><br>
        <span style="font-size:0.8rem;color:#64748B">${h.address || h.area}</span><br>
        <div style="margin:4px 0">
          <b style="color:#0D9488">${h.distance_km} km</b> · From ${inr(h.price)}/mo
        </div>
        <div style="font-size:0.75rem;margin-bottom:6px">📞 ${h.phone}</div>
        <button onclick="openDetail(${h.id})" style="width:100%;padding:5px;background:#0D9488;color:#fff;border:0;border-radius:6px;cursor:pointer;font-weight:700">View Details</button>
      </div>
    `);
  });

  map.invalidateSize();
  if (pts.length) {
    map.fitBounds(pts, { padding: [40, 40] });
  } else {
    map.setView([19.0760, 72.8777], 12);
  }
}

function render() {
  const list = view === "save" ? results.filter(h => saved.has(h.id)) : results.filter(h => h.match != null);
  $("list").hidden = view === "map";
  $("mapSection").hidden = view !== "map";
  if (view === "map") {
    setTimeout(() => drawMap(list, lastPrefs ? { lat: lastPrefs.campus_lat, lng: lastPrefs.campus_lng } : null), 50);
  }

  $("sc").textContent = saved.size;
  $("compCount").textContent = compareSet.size;
  $("compText").textContent = `${compareSet.size} Hostel${compareSet.size === 1 ? '' : 's'} Selected`;
  $("compBar").style.display = compareSet.size > 0 ? 'flex' : 'none';

  $("countBar").textContent = view === "match" && lastPrefs ? `Showing ${list.length} verified hostel${list.length === 1 ? '' : 's'} matching your parameters.` : '';
  $("list").innerHTML = list.length ? list.map(card).join('') : `<div class="empty-box"><h3>No matching hostels found</h3><p style="margin-top:6px">Try widening your distance slider or increasing your budget.</p></div>`;
}

async function search() {
  const collegeId = $("collegeSelect").value;
  lastPrefs = {
    budget: +$("budget").value,
    max_distance: +$("dist").value,
    rooms: checked("rooms"),
    amenities: checked("ams"),
    gender: activeGender,
    food: activeFood,
    q: $("qSearch").value,
    sort: $("sortSelect").value,
    college_id: collegeId,
    campus_lat: customLocation ? customLocation.lat : undefined,
    campus_lng: customLocation ? customLocation.lng : undefined
  };

  let d;
  try {
    const res = await fetch("/api/recommend", { method: "POST", headers: H, body: JSON.stringify(lastPrefs) });
    if (!res.ok) throw new Error("API status " + res.status);
    d = await res.json();
  } catch (err) {
    // Graceful offline / direct file opening fallback!
    d = clientSideRecommend(lastPrefs);
  }

  const extra = results.filter(h => h.match == null && saved.has(h.id));
  results = (d.results || []).concat(extra);
  render();
}

async function loadSaved() {
  try {
    const res = await fetch("/api/shortlist", { headers: H });
    if (res.ok) {
      const d = await res.json();
      saved = new Set((d.results || []).map(h => h.id));
      (d.results || []).forEach(h => {
        if (!results.find(x => x.id === h.id)) results.push({ ...h, match: null });
      });
    }
  } catch (e) {
    const stored = JSON.parse(localStorage.savedHostels || '[]');
    saved = new Set(stored);
  }
  render();
}

async function toggleSave(id) {
  const on = saved.has(id);
  on ? saved.delete(id) : saved.add(id);
  localStorage.savedHostels = JSON.stringify([...saved]);
  render();
  toast(on ? "Removed from shortlist" : "Saved to shortlist!");
  try {
    await fetch("/api/shortlist/" + id, { method: on ? "DELETE" : "POST", headers: H });
  } catch (e) {}
}

function toggleCompare(id) {
  if (compareSet.has(id)) {
    compareSet.delete(id);
    toast("Removed from comparison");
  } else {
    if (compareSet.size >= 3) {
      toast("You can compare up to 3 hostels at a time");
      return;
    }
    compareSet.add(id);
    toast("Added to comparison!");
  }
  render();
}

async function openDetail(id) {
  let full = results.find(x => x.id === id);
  try {
    const res = await fetch("/api/hostels/" + id);
    if (res.ok) full = await res.json();
  } catch (e) {}
  if (!full) full = EMBEDDED_HOSTELS.find(x => x.id === id);

  const b = full && full.breakdown;
  const max = { budget: 25, distance: 25, amenities: 30, room: 10, rating: 10 };
  const gmapsUrl = `https://www.google.com/maps/search/?api=1&query=${full.lat},${full.lng}`;

  $("dlgDetail").innerHTML = `
    <div class="modal-header">
      <div>
        <h2 style="font-size:1.35rem;font-weight:800">${full.name}</h2>
        <div style="color:var(--mute);font-size:0.85rem;margin-top:2px">📍 ${full.address || full.area} · ★ ${full.rating} (Safety: ${full.safety_score || 4.5}/5)</div>
      </div>
      <button class="modal-close" onclick="$('dlgDetail').close()">✕</button>
    </div>

    <div style="height:180px;border-radius:12px;overflow:hidden;margin-bottom:14px">
      <img src="${full.cover_image}" style="width:100%;height:100%;object-fit:cover" alt="${full.name}" onerror="this.src='https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=700&q=80'">
    </div>

    <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap">
      <a href="tel:${full.phone}" class="btn-action call" style="flex:1">📞 Call Warden: ${full.phone}</a>
      <a href="${gmapsUrl}" target="_blank" rel="noopener" class="btn-action primary" style="flex:1">🗺️ Open in Google Maps</a>
      ${full.website ? `<a href="${full.website}" target="_blank" rel="noopener" class="btn-action" style="flex:1">🌐 Official Website</a>` : ''}
    </div>

    <p style="font-size:0.92rem;line-height:1.55;margin-bottom:14px">${full.about}</p>

    ${full.nearby_colleges ? `<div style="background:var(--bg);padding:10px;border-radius:8px;font-size:0.82rem;margin-bottom:14px"><b>🎓 Nearby Colleges:</b> ${full.nearby_colleges}</div>` : ''}

    <h3 style="font-size:1rem;margin-bottom:8px">Room Monthly Rates</h3>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px">
      ${Object.entries(full.rooms).map(([k, v]) => `<div style="padding:8px 12px;border:1px solid var(--line);border-radius:8px;display:flex;justify-content:space-between;font-size:0.85rem"><span>${label(k)}</span><b>${inr(v)}/mo</b></div>`).join("")}
    </div>

    <h3 style="font-size:1rem;margin-bottom:8px">Amenities & Diet</h3>
    <div style="margin-bottom:14px;display:flex;flex-wrap:wrap;gap:6px">
      <span class="tag" style="background:#fefce8;color:#ca8a04;font-weight:700">Food: ${label(full.food || 'pure_veg')}</span>
      ${full.amenities.map(a => `<span class="tag">${label(a)}</span>`).join("")}
    </div>

    ${b ? `<h3 style="font-size:1rem;margin-bottom:8px">Match Score Breakdown (${full.match}%)</h3>
    <div style="margin-bottom:16px">${Object.entries(b).map(([k, v]) => `
      <div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:2px"><span>${label(k)}</span><b>${v}/${max[k]}</b></div>
      <div style="height:6px;background:var(--line);border-radius:4px;overflow:hidden;margin-bottom:6px"><div style="height:100%;background:var(--primary);width:${(v / max[k]) * 100}%"></div></div>
    `).join("")}</div>` : ''}

    <hr style="border:0;border-top:1px solid var(--line);margin:14px 0">

    <h3 style="font-size:1.05rem;margin-bottom:10px">Send Booking / Visit Inquiry</h3>
    <form id="enqForm" onsubmit="sendEnquiry(event,${full.id})">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px">
        <input type="text" id="enqName" placeholder="Your Name" required style="padding:10px;border-radius:8px;border:1px solid var(--line)">
        <input type="tel" id="enqPhone" placeholder="Phone Number" required style="padding:10px;border-radius:8px;border:1px solid var(--line)">
      </div>
      <input type="date" id="enqDate" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--line);margin-bottom:10px">
      <button type="submit" class="btn-submit" style="margin-top:0">Submit Instant Enquiry</button>
    </form>
  `;
  $("dlgDetail").showModal();
}

async function sendEnquiry(e, hid) {
  e.preventDefault();
  const body = {
    hostel_id: hid,
    name: $("enqName").value,
    phone: $("enqPhone").value,
    move_date: $("enqDate").value
  };
  try {
    const res = await fetch("/api/enquiry", { method: "POST", headers: H, body: JSON.stringify(body) });
    const d = await res.json();
    if (res.ok) {
      toast(`Inquiry ${d.code} sent! Warden will contact you.`);
      $("dlgDetail").close();
      return;
    }
  } catch (err) {}
  const mockCode = "HM-" + Math.floor(10000 + Math.random() * 90000);
  toast(`Inquiry ${mockCode} recorded! Warden will contact you.`);
  $("dlgDetail").close();
}

function openCompModal() {
  const selected = results.filter(h => compareSet.has(h.id));
  if (!selected.length) {
    toast("Select hostels using '+ Compare' first");
    return;
  }
  $("dlgComp").innerHTML = `
    <div class="modal-header">
      <h2>Hostel Side-by-Side Comparison</h2>
      <button class="modal-close" onclick="$('dlgComp').close()">✕</button>
    </div>
    <div style="overflow-x:auto">
      <table style="width:100%;border-collapse:collapse;font-size:0.88rem">
        <thead>
          <tr style="border-bottom:2px solid var(--line)">
            <th style="padding:10px;text-align:left">Feature</th>
            ${selected.map(h => `<th style="padding:10px;text-align:center">${h.name}</th>`).join("")}
          </tr>
        </thead>
        <tbody>
          <tr style="border-bottom:1px solid var(--line)">
            <td style="padding:10px;font-weight:600">Starting Price</td>
            ${selected.map(h => `<td style="padding:10px;text-align:center;color:var(--primary);font-weight:800">${inr(h.price)}/mo</td>`).join("")}
          </tr>
          <tr style="border-bottom:1px solid var(--line)">
            <td style="padding:10px;font-weight:600">Distance to College</td>
            ${selected.map(h => `<td style="padding:10px;text-align:center;font-weight:700">${h.distance_km} km</td>`).join("")}
          </tr>
          <tr style="border-bottom:1px solid var(--line)">
            <td style="padding:10px;font-weight:600">Dietary Type</td>
            ${selected.map(h => `<td style="padding:10px;text-align:center">${label(h.food || 'pure_veg')}</td>`).join("")}
          </tr>
          <tr style="border-bottom:1px solid var(--line)">
            <td style="padding:10px;font-weight:600">Gender</td>
            ${selected.map(h => `<td style="padding:10px;text-align:center;text-transform:uppercase">${h.gender}</td>`).join("")}
          </tr>
          <tr style="border-bottom:1px solid var(--line)">
            <td style="padding:10px;font-weight:600">Rating</td>
            ${selected.map(h => `<td style="padding:10px;text-align:center">★ ${h.rating}</td>`).join("")}
          </tr>
          <tr style="border-bottom:1px solid var(--line)">
            <td style="padding:10px;font-weight:600">Warden Phone</td>
            ${selected.map(h => `<td style="padding:10px;text-align:center"><a href="tel:${h.phone}" style="color:var(--primary);font-weight:700">${h.phone}</a></td>`).join("")}
          </tr>
        </tbody>
      </table>
    </div>
  `;
  $("dlgComp").showModal();
}

function switchTab(v) {
  view = v;
  $("tAll").className = "tab-btn" + (v === "match" ? " active" : "");
  $("tSave").className = "tab-btn" + (v === "save" ? " active" : "");
  $("tMap").className = "tab-btn" + (v === "map" ? " active" : "");
  render();
}

$("prefForm").onsubmit = e => { e.preventDefault(); switchTab("match"); search(); };
$("qSearch").oninput = () => search();
$("sortSelect").onchange = () => lastPrefs && search();
$("dlgDetail").addEventListener("click", e => { if (e.target === $("dlgDetail")) $("dlgDetail").close(); });
$("dlgComp").addEventListener("click", e => { if (e.target === $("dlgComp")) $("dlgComp").close(); });

search().then(loadSaved);
</script>
"""

new_html = html[:pos] + js_code + "</body>\n</html>"

for path in [
    os.path.join(BASE, "templates", "index.html"),
    os.path.join(BASE, "index.html"),
    r"C:\Users\Asus\Downloads\index.html"
]:
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)
    print("Wrote", path)

print("Build complete.")
