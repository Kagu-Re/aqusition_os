// Shared UI components and helper functions for console

// ===== Utility Functions =====

function q(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : "";
}

function getCookie(name) {
  const m = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[.$?*|{}()\[\]\\\/\+^]/g, '\\$&') + '=([^;]*)'));
  return m ? decodeURIComponent(m[1]) : "";
}

function secretHeader() {
  const s = (document.getElementById("secret")?.value || "").trim();
  return s ? {"X-AE-SECRET": s} : {};
}

function isoDay(d) {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

function fmt(n, digits = 2) {
  if (n === null || n === undefined) return "—";
  if (typeof n !== "number") return String(n);
  return n.toFixed(digits);
}

function fmtInt(n) {
  if (n === null || n === undefined) return "—";
  return String(Math.trunc(n));
}

// ===== API Functions =====

async function apiFetch(url, opts = {}) {
  const csrf = getCookie("ae_csrf");
  const csrfHeader = csrf ? {"X-AE-CSRF": csrf} : {};
  const headers = Object.assign({"content-type": "application/json"}, secretHeader(), csrfHeader, (opts.headers || {}));
  const init = Object.assign({credentials: "include"}, opts, {headers});
  return fetch(url, init);
}

async function api(path, opts = {}) {
  const headers = opts.headers || {};
  // If you set window.AE_SECRET in DevTools, it will be used.
  if (window.AE_SECRET) headers["X-AE-SECRET"] = window.AE_SECRET;
  opts.headers = headers;
  const res = await apiFetch(path, opts);
  const text = await res.text();
  let data = null;
  try { data = JSON.parse(text); } catch (e) {}
  if (!res.ok) throw new Error((data && data.detail) ? data.detail : text);
  return data;
}

// ===== UI Components =====

function badge(status) {
  const s = String(status || "no_data");
  let color = "#8888a0";
  let bgColor = "rgba(136, 136, 160, 0.1)";
  let borderColor = "#2a2a3e";
  
  if (s.toLowerCase().includes("scale") || s.toLowerCase().includes("good")) {
    color = "#00ff88";
    bgColor = "rgba(0, 255, 136, 0.1)";
    borderColor = "#00ff88";
  } else if (s.toLowerCase().includes("hold") || s.toLowerCase().includes("warning")) {
    color = "#ffd700";
    bgColor = "rgba(255, 215, 0, 0.1)";
    borderColor = "#ffd700";
  } else if (s.toLowerCase().includes("cut") || s.toLowerCase().includes("error") || s.toLowerCase().includes("failed")) {
    color = "#ff0040";
    bgColor = "rgba(255, 0, 64, 0.1)";
    borderColor = "#ff0040";
  }
  
  return `<span class="badge" style="color: ${color}; background: ${bgColor}; border-color: ${borderColor}; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; border: 1px solid;">${s}</span>`;
}

function card(label, value, sub, color = "#00f0ff") {
  const el = document.createElement("div");
  el.className = "card";
  el.style.cssText = "padding: 16px; border-color: #2a2a3e;";
  el.innerHTML = `<div class="text-xs mb-2" style="color: #8888a0; text-transform: uppercase; letter-spacing: 0.05em;">${label}</div>
                  <div class="text-xl font-bold mb-1" style="color: ${color};">${value}</div>
                  <div class="text-xs" style="color: #555566;">${sub || ""}</div>`;
  return el;
}

function createSummaryCard(label, value, subtitle = "", color = "#00f0ff") {
  const card = document.createElement("div");
  card.className = "rounded-lg border p-4";
  card.style.cssText = `background: #1e1e2e; border-color: #2a2a3e;`;
  card.innerHTML = `
    <div class="text-xs mb-1" style="color: #8888a0;">${label}</div>
    <div class="text-2xl font-bold mb-1" style="color: ${color};">${value}</div>
    ${subtitle ? `<div class="text-xs" style="color: #8888a0;">${subtitle}</div>` : ""}
  `;
  return card;
}

function sparkline(series, valueKey, height = 64) {
  const w = 320;
  const h = height;
  const pad = 6;

  const vals = (series || []).map(x => Number(x[valueKey] ?? x.value ?? x.count ?? 0));
  if (!vals.length) return `<div class="text-xs" style="color: #555566;">(no data)</div>`;
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const rng = (max - min) || 1;

  const pts = vals.map((v, i) => {
    const x = pad + (i * (w - pad*2) / Math.max(1, vals.length - 1));
    const y = pad + ((max - v) * (h - pad*2) / rng);
    return [x, y];
  });

  const path = pts.map((p,i)=> (i===0?`M ${p[0]} ${p[1]}`:`L ${p[0]} ${p[1]}`)).join(" ");
  return `<svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}" style="filter: drop-shadow(0 0 2px currentColor);">
    <path d="${path}" fill="none" stroke="currentColor" stroke-width="2" opacity="0.9"></path>
  </svg>`;
}

// ===== Loading/Empty/Error States =====

function showLoading(container) {
  if (typeof container === 'string') {
    container = document.getElementById(container);
  }
  if (container) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="spinner" style="margin: 0 auto;"></div>
        <div class="empty-state-title mt-4">Loading...</div>
      </div>
    `;
  }
}

function showEmptyState(container, icon = "📋", title = "No data", description = "") {
  if (typeof container === 'string') {
    container = document.getElementById(container);
  }
  if (container) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon" style="font-size: 64px; opacity: 0.6;">${icon}</div>
        <div class="empty-state-title" style="font-size: 18px; margin-bottom: 12px;">${title}</div>
        ${description ? `<div class="empty-state-description" style="font-size: 14px;">${description}</div>` : ""}
      </div>
    `;
  }
}

function showError(container, message) {
  if (typeof container === 'string') {
    container = document.getElementById(container);
  }
  if (container) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon" style="color: #ff0040;">⚠️</div>
        <div class="empty-state-title" style="color: #ff0040;">Error</div>
        <div class="empty-state-description">${message}</div>
      </div>
    `;
  }
}

// ===== Auth Functions =====

function showAuthMsg(obj) {
  const el = document.getElementById("auth_msg");
  if (el) {
    el.classList.remove("hidden");
    el.textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
  }
}

async function refreshMe() {
  const who = document.getElementById("whoami");
  if (!who) return;
  try {
    const r = await apiFetch("/api/auth/me");
    if (!r.ok) {
      who.textContent = "anon";
      return;
    }
    const j = await r.json();
    who.textContent = `${j.username} (${j.role})`;
  } catch (e) {
    who.textContent = "…";
  }
}

async function login() {
  const u = (document.getElementById("login_user")?.value || "").trim();
  const p = (document.getElementById("login_pass")?.value || "").trim();
  if (!u || !p) {
    toast.error("Missing username/password");
    return showAuthMsg("missing username/password");
  }
  try {
    const r = await apiFetch("/api/auth/login", {method: "POST", body: JSON.stringify({username: u, password: p})});
    const j = await r.json().catch(()=>({}));
    if (!r.ok) {
      toast.error(j.detail || "Login failed");
      return showAuthMsg(j.detail || j || "login failed");
    }
    toast.success(`Logged in as ${u}`);
    showAuthMsg(j);
    await refreshMe();
  } catch (e) {
    toast.error("Login error: " + e.message);
    showAuthMsg("Login error: " + e.message);
  }
}

async function logout() {
  try {
    const r = await apiFetch("/api/auth/logout", {method: "POST", body: "{}"});
    const j = await r.json().catch(()=>({}));
    toast.info("Logged out");
    showAuthMsg(j);
    await refreshMe();
  } catch (e) {
    toast.error("Logout error: " + e.message);
  }
}

function loadSecret() {
  const secretEl = document.getElementById("secret");
  if (secretEl) {
    const stored = localStorage.getItem("ae_secret");
    if (stored) {
      secretEl.value = stored;
      window.AE_SECRET = stored;
    }
    secretEl.addEventListener("input", (e) => {
      const val = e.target.value.trim();
      if (val) {
        localStorage.setItem("ae_secret", val);
        window.AE_SECRET = val;
      } else {
        localStorage.removeItem("ae_secret");
        delete window.AE_SECRET;
      }
    });
  }
}

// ===== Health Check =====

async function checkHealth() {
  const healthEl = document.getElementById("health-text");
  const indicatorEl = document.getElementById("health-indicator");
  if (!healthEl || !indicatorEl) return;
  
  try {
    const data = await api("/api/health");
    if (data.ok) {
      healthEl.textContent = "OK" + (data.version ? (" • v" + data.version) : "");
      healthEl.style.color = "#00ff88";
      indicatorEl.className = "status-dot ok";
    } else {
      healthEl.textContent = "BAD" + (data.version ? (" • v" + data.version) : "");
      healthEl.style.color = "#ffd700";
      indicatorEl.className = "status-dot warn";
    }
    const badge = document.getElementById("version-badge");
    if (badge && data.version) badge.textContent = "v" + data.version;
  } catch (e) {
    healthEl.textContent = "ERR";
    healthEl.style.color = "#ff0040";
    indicatorEl.className = "status-dot error";
  }
}

// ===== Search Functions =====

function closeSearchResults() {
  const resultsEl = document.getElementById('search-results');
  const searchEl = document.getElementById('global-search');
  if (resultsEl) resultsEl.classList.add('hidden');
  if (searchEl) searchEl.value = '';
}

async function handleGlobalSearch(event) {
  const query = event.target.value.trim();
  const resultsEl = document.getElementById('search-results');
  const contentEl = document.getElementById('search-results-content');
  
  if (query.length < 2) {
    if (resultsEl) resultsEl.classList.add('hidden');
    return;
  }
  
  if (resultsEl) resultsEl.classList.remove('hidden');
  if (contentEl) {
    contentEl.innerHTML = '<div class="text-center py-4"><div class="spinner" style="margin: 0 auto;"></div><div class="mt-2 text-sm" style="color: #8888a0;">Searching...</div></div>';
  }
  
  try {
    const db = q("db") || "acq.db";
    const results = {
      leads: [],
      events: [],
      pages: []
    };
    
    // Search leads
    try {
      const leadsData = await api(`/api/leads?db=${db}&limit=50`);
      const leads = (leadsData.items || []).filter(l => {
        const searchText = `${l.name || ''} ${l.email || ''} ${l.phone || ''} ${l.message || ''} ${l.utm_campaign || ''}`.toLowerCase();
        return searchText.includes(query.toLowerCase());
      });
      results.leads = leads.slice(0, 10);
    } catch (e) {}
    
    // Search events
    try {
      const eventsData = await api(`/api/events?db=${db}&limit=50`);
      const events = (eventsData.items || []).filter(e => {
        const searchText = `${e.page_id || ''} ${e.event_name || ''} ${JSON.stringify(e.params_json || {})}`.toLowerCase();
        return searchText.includes(query.toLowerCase());
      });
      results.events = events.slice(0, 10);
    } catch (e) {}
    
    // Search pages
    try {
      const pagesData = await api(`/api/pages?db=${db}&limit=50`);
      const pages = (pagesData.items || []).filter(p => {
        const searchText = `${p.page_id || ''} ${p.headline || ''} ${p.client_id || ''}`.toLowerCase();
        return searchText.includes(query.toLowerCase());
      });
      results.pages = pages.slice(0, 10);
    } catch (e) {}
    
    // Render results
    renderSearchResults(results, query);
  } catch (e) {
    if (contentEl) {
      contentEl.innerHTML = `<div class="text-center py-4 text-sm" style="color: #ff0040;">Error: ${e.message}</div>`;
    }
  }
}

function renderSearchResults(results, query) {
  const contentEl = document.getElementById('search-results-content');
  if (!contentEl) return;
  
  const total = results.leads.length + results.events.length + results.pages.length;
  
  if (total === 0) {
    contentEl.innerHTML = '<div class="text-center py-8 text-sm" style="color: #8888a0;">No results found</div>';
    return;
  }
  
  let html = `<div class="text-xs mb-4" style="color: #8888a0;">Found ${total} result(s) for "${query}"</div>`;
  
  // Leads results
  if (results.leads.length > 0) {
    html += `<div class="mb-6"><div class="text-sm font-bold mb-2" style="color: #00f0ff;">Leads (${results.leads.length})</div>`;
    results.leads.forEach(lead => {
      html += `
        <div class="p-3 mb-2 rounded border cursor-pointer hover:bg-neutral-800" style="background: #1e1e2e; border-color: #2a2a3e;" onclick="navigateTo('/leads'); setTimeout(() => { if (typeof loadLeads === 'function') loadLeads(); }, 500);">
          <div class="text-sm font-bold" style="color: #00f0ff;">#${lead.lead_id}</div>
          <div class="text-xs mt-1" style="color: #e0e0e8;">${lead.name || ''} ${lead.email || ''} ${lead.phone || ''}</div>
          <div class="text-xs mt-1" style="color: #8888a0;">${lead.message || ''}</div>
        </div>
      `;
    });
    html += `</div>`;
  }
  
  // Events results
  if (results.events.length > 0) {
    html += `<div class="mb-6"><div class="text-sm font-bold mb-2" style="color: #00ff88;">Events (${results.events.length})</div>`;
    results.events.forEach(event => {
      html += `
        <div class="p-3 mb-2 rounded border cursor-pointer hover:bg-neutral-800" style="background: #1e1e2e; border-color: #2a2a3e;" onclick="navigateTo('/events'); setTimeout(() => { if (typeof loadEvents === 'function') loadEvents(); }, 500);">
          <div class="text-sm font-bold" style="color: #00ff88;">${event.event_name || 'unknown'}</div>
          <div class="text-xs mt-1" style="color: #e0e0e8;">Page: ${event.page_id || '-'}</div>
          <div class="text-xs mt-1 font-mono" style="color: #8888a0;">${new Date(event.timestamp).toLocaleString()}</div>
        </div>
      `;
    });
    html += `</div>`;
  }
  
  // Pages results
  if (results.pages.length > 0) {
    html += `<div class="mb-6"><div class="text-sm font-bold mb-2" style="color: #00f0ff;">Pages (${results.pages.length})</div>`;
    results.pages.forEach(page => {
      html += `
        <div class="p-3 mb-2 rounded border cursor-pointer hover:bg-neutral-800" style="background: #1e1e2e; border-color: #2a2a3e;" onclick="navigateTo('/pages'); setTimeout(() => { if (typeof loadPages === 'function') loadPages(); }, 500);">
          <div class="text-sm font-bold font-mono" style="color: #00f0ff;">${page.page_id || '-'}</div>
          <div class="text-xs mt-1" style="color: #e0e0e8;">${page.headline || ''}</div>
          <div class="text-xs mt-1" style="color: #8888a0;">Client: ${page.client_id || '-'}</div>
        </div>
      `;
    });
    html += `</div>`;
  }
  
  contentEl.innerHTML = html;
}

// Helper for navigation
function navigateTo(path) {
  if (window.router) {
    window.router.navigate(path);
  } else {
    window.location.hash = path;
  }
}
