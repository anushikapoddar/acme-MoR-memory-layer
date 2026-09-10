'use strict';
/* Merchant Risk Memory -- Acme MoR underwriting console.
   Vanilla JS, no framework, no build step. Every number on every screen comes
   from an endpoint that computed it; nothing here is a placeholder. */

const $ = (s, r = document) => r.querySelector(s);
let toastTimer;
function toast(msg) {
  const el = $('#toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('on'), 3200);
}
const api = async (p, opts) => {
  const r = await fetch(p, opts);
  const text = await r.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = {}; }
  if (!r.ok) throw new Error((data && data.error) || `${p} -> ${r.status}`);
  return data;
};
const post = (p, body) => api(p, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body || {}),
});

const esc = (s) => String(s ?? '').replace(/[&<>"']/g,
  (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = (n, d = 1) => `${(n * 100).toFixed(d)}%`;
const usd = (n) => n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M`
  : n >= 1e3 ? `$${Math.round(n / 1e3)}k` : `$${Math.round(n)}`;
const money = (n) => `$${Math.round(n).toLocaleString()}`;

/** Probability meter: one number on a 0–100% track. The recommendation already
    encodes the operating point; the bar does not restate a decline line. */
function pBadMeter(p, _threshold, tone) {
  const pPos = Math.min(96, Math.max(3, p * 100));
  const pin = tone === 'ok' ? 'ok' : (tone === 'warn' || tone === 'high') ? 'warn' : 'bad';
  const pinSide = pPos < 16 ? 'left' : pPos > 78 ? 'right' : 'mid';
  return `<div class="pbar" role="img"
    aria-label="${pct(p)} probability of going bad">
    <div class="pbar-track">
      <i class="pbar-fill ${pin}" style="width:${pPos.toFixed(1)}%"></i>
      <b class="pin ${pin}" style="left:${pPos.toFixed(1)}%"></b>
    </div>
    <div class="pbar-you-row">
      <span class="pbar-you ${pinSide}" style="left:${pPos.toFixed(1)}%">${pct(p)}</span>
    </div>
    <div class="pbar-scale">
      <span>0%</span>
      <span>100%</span>
    </div>
  </div>`;
}

function recChain(d) {
  const contribs = d.contributions || [];
  if (!contribs.length) {
    return `<p class="rec-unchanged">Unchanged from the ${pct(d.prior)} portfolio base rate — no signals or precedent moved the odds.</p>`;
  }
  const steps = [`<div class="rec-step"><span>Base rate</span><b>${pct(d.prior)}</b></div>`];
  contribs.forEach((c) => {
    steps.push(`<span class="rec-op" aria-hidden="true">×</span>
      <div class="rec-step"><span>${esc(c.title)}</span><b>×${c.applied_lr}</b></div>`);
  });
  steps.push(`<span class="rec-op" aria-hidden="true">→</span>
    <div class="rec-step out"><span>P(bad)</span><b>${pct(d.p_bad)}</b></div>`);
  return `<div class="rec-chain">${steps.join('')}</div>`;
}

function recCosts(d) {
  const aWin = d.expected_cost_approve < d.expected_cost_decline;
  return `<div class="rec-costs">
    <div class="rec-cost${aWin ? ' win' : ''}">
      <span>Expected cost of approving</span>
      <b>${money(d.expected_cost_approve)}</b>
      ${aWin ? '<em>cheaper path</em>' : ''}
    </div>
    <div class="rec-cost${!aWin ? ' win' : ''}">
      <span>Expected cost of declining</span>
      <b>${money(d.expected_cost_decline)}</b>
      ${!aWin ? '<em>cheaper path</em>' : ''}
    </div>
  </div>`;
}

function recWhy(b, d) {
  const points = b.why || [];
  const hasMath = (d.contributions && d.contributions.length) || d.p_bad != null;
  if (!points.length && !b.explanation && !hasMath) return '';
  return `<div class="rec-why">
    <h3>Why this recommendation?</h3>
    ${points.length ? `<ul class="rec-points">${points.map((w) => `<li>${esc(w)}</li>`).join('')}</ul>` : ''}
    ${b.explanation ? `<p>${esc(b.explanation).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</p>` : ''}
    <details class="rec-math">
      <summary>The calculation</summary>
      ${recChain(d)}
      ${recCosts(d)}
    </details>
  </div>`;
}

function webCard(web) {
  if (!web) return '';
  const st = web.status || 'skipped';
  const label = {
    found: 'Public pages found', empty: 'No public pages found',
    error: 'Lookup failed', skipped: 'Lookup skipped',
  }[st] || st;
  const hits = web.hits || [];
  const themes = web.themes || [];
  const hitHtml = hits.length
    ? `<ul class="web-hits">${hits.map((h) => `<li>
        ${h.url ? `<a href="${esc(h.url)}" target="_blank" rel="noopener">${esc(h.title)}</a>`
                : `<strong>${esc(h.title)}</strong>`}
        <span class="tiny muted"> ${esc(h.source || '')}</span>
        <div class="tiny muted">${esc(h.snippet || '')}</div></li>`).join('')}</ul>`
    : `<p class="tiny muted">${esc(web.reason || 'Nothing retrieved.')}</p>`;
  const themeHtml = themes.length
    ? `<p class="tiny">Flagged on the open web: ${themes.map((t) => esc(t.theme.replace(/_/g, ' '))).join(', ')}</p>`
    : '';
  return `<div class="web-box">
    <div class="k mono tiny muted">OPEN WEB</div>
    <div class="web-label">${esc(label)}</div>
    <p class="tiny muted">Query: ${esc(web.query || '—')}</p>
    ${hitHtml}${themeHtml}
  </div>`;
}
const LABEL = {
  ai_product: 'AI product', saas: 'SaaS', digital_goods: 'Digital goods',
  ebooks_publications: 'Ebooks & publications', templates_plugins_apps: 'Templates & plugins',
  marketing_outreach: 'Marketing outreach', ai_content_generation: 'AI content generation',
  productized_services: 'Productized services',
  saas_ai_digital: 'SaaS / AI / Digital', edtech: 'Edtech', services: 'Services',
  financial_services: 'Financial services', physical_products: 'Physical products',
  gaming: 'Gaming', marketplace: 'Marketplace', others: 'Others',
  manual_digital_services: 'Manual digital services',
  unlicensed_financial: 'Financial products', physical_goods: 'Physical goods',
  gaming_virtual_goods: 'Gaming / virtual goods', marketplace_resale: 'Marketplace',
};
const title = (s) => LABEL[s]
  || String(s || '').replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());
const initials = (s) => String(s || '?').split(/\s+/).slice(0, 2)
  .map((w) => w[0]).join('').toUpperCase();

/* Stroke icons, 24x24, drawn inline so the page stays self-contained. */
const ICON = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
  check: '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
  brain: '<path d="M12 4.5a3 3 0 0 0-5.9.7A3 3 0 0 0 4 10a3 3 0 0 0 1.4 4.7A3 3 0 0 0 9 20a3 3 0 0 0 3-2z"/><path d="M12 4.5a3 3 0 0 1 5.9.7A3 3 0 0 1 20 10a3 3 0 0 1-1.4 4.7A3 3 0 0 1 15 20a3 3 0 0 1-3-2z"/>',
  graph: '<circle cx="5" cy="6" r="2.5"/><circle cx="19" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M7.2 7.4L10.4 16M16.8 7.4L13.6 16M7.5 6h9"/>',
  bell: '<path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 1.9"/>',
  shield: '<path d="M12 22s8-3.4 8-9.4V5.6L12 2.5 4 5.6v7c0 6 8 9.4 8 9.4z"/><path d="M12 8.5v4M12 15.8v.1"/>',
  chart: '<path d="M3 3v18h18"/><path d="M7 15l3.5-4 3 2.5L20 7"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  chev: '<polyline points="9 5 16 12 9 19"/>',
  down: '<polyline points="6 9 12 15 18 9"/>',
  up: '<polyline points="18 15 12 9 6 15"/>',
  bolt: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
  file: '<path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7z"/><polyline points="14 2 14 7 19 7"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
};
const svg = (name, cls = '') =>
  `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON[name] || ''}</svg>`;

const VIEWS = [
  ['homepage', 'Homepage', 'grid'],
  ['history', 'Assessment history', 'clock'],
  ['merchants', 'Merchants', 'users'],
  ['memory', 'Memory layer', 'brain'],
  ['cases', 'Evaluations', 'check'],
  ['graph', 'Context graph', 'graph'],
  ['alerts', 'Alerts', 'bell'],
];

const state = {
  view: 'homepage', portfolio: null, briefId: null,
  dir: { q: '', band: '', page: 0 },
  assessResult: null, assessFrom: null,
  assessMode: 'import', assessDraft: null, applications: null,
};

function renderNav() {
  const p = state.portfolio || {};
  const counts = {
    cases: p.queue_size, alerts: p.alert_total,
    memory: p.memory && p.memory.active,
    history: p.assessment_count,
};
  $('#nav').innerHTML = VIEWS.map(([id, label, icon]) => {
    const n = counts[id];
    return `<a data-view="${id}" class="${state.view === id ? 'on' : ''}" tabindex="0">
      ${svg(icon)}<span>${label}</span>${n ? `<span class="count">${n}</span>` : ''}</a>`;
  }).join('');
  $('#nav').querySelectorAll('a').forEach((a) => {
    a.onclick = () => go(a.dataset.view);
    a.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(a.dataset.view); } };
  });

  const m = p.memory || {};
  $('#st-mem').textContent = m.active != null ? m.active : '—';
  $('#st-when').textContent = p.last_reconciled || 'never';
  const conf = m.mean_confidence != null ? m.mean_confidence : 0;
  $('#st-bar').style.width = `${Math.round(conf * 100)}%`;
  $('#st-bar').parentElement.title = `Mean confidence across active memories: ${pct(conf)}`;
  const dot = $('#belldot');
  if (dot) dot.hidden = !(p.queue_size || p.alert_total);
}

function go(view, id) {
  state.view = view; state.briefId = id || null;
  if (view === 'merchants') state.dir.page = 0;
  if (view !== 'assess') {
    state.assessResult = null;
    state.assessFrom = null;
  }
  renderNav(); render();
}

/* Homepage has its own greeting + assess CTA; the global search belongs
   on directory-style views. Hide it (and empty topbar space) there. */
function syncTopbar() {
  const hide = state.view === 'homepage' && !state.briefId;
  const bar = document.querySelector('.topbar');
  const search = bar && bar.querySelector('.search');
  if (search) search.hidden = hide;
  if (bar) bar.classList.toggle('nosearch', hide);
}

/* Page header. `right` holds the period selector and primary action. */
function head(t, sub, right) {
  return `<div class="pagehead"><div><h2>${t}</h2><p>${sub}</p></div>
    <div class="acts">${right || ''}</div></div>`;
}
function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

/* ------------------------------------------------------------- overview */
function statCard(s) {
  const dir = s.up ? 'up' : 'down';
  const arrow = s.up ? ICON.up : ICON.down;
  const delta = s.delta ? `<span class="d ${dir}">
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor"
             stroke-width="2.6" stroke-linecap="round" aria-hidden="true">${arrow}</svg>
        ${esc(s.delta)}</span><span class="vs">vs prior 30d</span>` : '';
  return `<div class="stat"><div>
      <div class="k">${esc(s.k)}</div>
      <div class="v">${esc(s.v)}${delta}</div>
      ${s.note ? `<div class="n">${esc(s.note)}</div>` : ''}
    </div><div class="ic ${s.tone}">${svg(s.icon)}</div></div>`;
}

/* Donut, hand-drawn as stroked arcs on one circle. r=54, C=2*pi*54. */
function donut(dist, total) {
  const C = 2 * Math.PI * 54;
  let at = 0;
  const arcs = dist.filter((d) => d.count > 0).map((d) => {
    const len = (d.count / total) * C;
    const seg = `<circle class="sw" cx="70" cy="70" r="54" fill="none"
      stroke="var(--${d.tone === 'ok' ? 'ok' : d.tone === 'warn' ? 'brand-yellow' : d.tone})"
      stroke-width="22" stroke-dasharray="${Math.max(len - 1.5, 0.6)} ${C - Math.max(len - 1.5, 0.6)}"
      stroke-dashoffset="${-at}" transform="rotate(-90 70 70)"><title>${esc(d.name)}: ${d.count}</title></circle>`;
    at += len;
    return seg;
  }).join('');
  return `<div class="donut">
    <svg viewBox="0 0 140 140" role="img" aria-label="Merchant risk distribution">
      <circle cx="70" cy="70" r="54" fill="none" stroke="var(--surface-3)" stroke-width="22"/>
      ${arcs}
      <text class="mid" x="70" y="66" text-anchor="middle" font-size="20" fill="var(--ink)">${total.toLocaleString()}</text>
      <text x="70" y="82" text-anchor="middle" font-size="9" fill="var(--muted)">merchants</text>
    </svg>
    <div class="legend">${dist.map((d) => `<div class="row">
      <i class="sw-${d.tone}"></i><b>${esc(d.name)}</b>
      <span class="n">${d.count.toLocaleString()} &middot; ${d.pct}%</span></div>`).join('')}
      <p class="tiny muted" style="margin:4px 0 0">Bands are cut at the operating point
        (${pct(0.1379)}) — not arbitrary quintiles.</p>
    </div></div>`;
}

async function viewHomepage() {
  const [o, p] = await Promise.all([api('/api/overview'), api('/api/portfolio')]);
  state.portfolio = p; renderNav();

  return head(`${greeting()}, Anushika`,
    'Portfolio risk, recent evaluations, and the live book.',
    `<button class="btn-primary" id="newapp">${svg('plus')} Assess a merchant</button>`)
  + `<div class="stats">${o.stats.map(statCard).join('')}</div>
  <div class="cols">
    <div>
      <div class="card"><h3>Merchant risk distribution
        <span class="hint">P(bad) across ${o.distribution_total.toLocaleString()} live merchants</span></h3>
        ${donut(o.distribution, o.distribution_total)}</div>

      <div class="card"><h3>Merchant directory
        <a data-view="merchants">View all &rsaquo;</a></h3>
        <div id="dirmount"><div class="empty"><span class="spinner"></span>Loading…</div></div></div>
    </div>
    <div>
      <div class="card"><h3>Portfolio exposure</h3>
        <div class="rows">
          <div class="rowitem" style="cursor:default"><div class="sq" style="background:var(--ok-bg);color:var(--ok)">${svg('bolt')}</div>
            <div class="nm">Annualised volume<span>${p.approved.toLocaleString()} approved merchants</span></div>
            <span class="chip c-mute">${usd(p.annual_volume)}</span></div>
          <div class="rowitem" style="cursor:default"><div class="sq" style="background:var(--warn-bg);color:var(--warn)">${svg('shield')}</div>
            <div class="nm">Prepaid liability<span>Undelivered subscription value we are on the hook for</span></div>
            <span class="chip c-mute">${usd(p.prepaid_exposure)}</span></div>
          <div class="rowitem" data-view="cases"><div class="sq" style="background:var(--bad-bg);color:var(--bad)">${svg('users')}</div>
            <div class="nm">Needs a human<span>Above ${pct(0.1379)} or carrying a live alert</span></div>
            <span class="chip c-bad">${(p.queue_size + p.alert_total).toLocaleString()}</span>
            ${svg('chev', 'chev')}</div>
        </div></div>

      <div class="card"><h3>Recent evaluations <a data-view="cases">All &rsaquo;</a></h3>
        <div class="rows">${o.recent.map((r) => `
          <div class="rowitem" data-id="${esc(r.id)}">
            <div class="sq" style="background:var(--surface-3);color:var(--ink-2)">${esc(initials(r.name))}</div>
            <div class="nm">${esc(r.name)}${r.real ? ' <span class="real">ACME</span>' : ''}
              <span>${esc(title(r.category))} &middot; ${esc(r.status)}</span></div>
            <span class="chip c-${r.tone}">${esc(r.band)}</span>
            <span class="when">${esc(r.when)}</span>
            ${svg('chev', 'chev')}</div>`).join('')
          || '<div class="empty">No evaluations yet.</div>'}</div></div>
    </div>
  </div>`;
}

/* ------------------------------------------------------------ merchants */
const PAGE_SIZE = 25;

function dirTable(d, compact) {
  if (!d.rows.length) return '<div class="empty">No merchants match that filter.</div>';
  return `<div class="scroll"><table>
    <thead><tr><th>Merchant</th><th>Category</th><th>Risk level</th>
      <th class="num">Memory score</th><th class="num">Monthly volume</th>
      ${compact ? '' : '<th>Last evaluated</th>'}</tr></thead>
    <tbody>${d.rows.map((r) => `<tr class="click" data-id="${esc(r.id)}">
      <td><b>${esc(r.name)}</b>${r.real ? ' <span class="real">ACME</span>' : ''}
        <div class="tiny muted mono">${esc(r.domain)} &middot; ${esc(r.country)}</div></td>
      <td class="tiny">${esc(title(r.category))}</td>
      <td><span class="chip c-${r.tone}">${esc(r.band)}</span></td>
      <td class="num"><b>${r.score}</b><span class="muted tiny">/100</span></td>
      <td class="num">${r.volume ? money(r.volume) : '<span class="muted">not live</span>'}</td>
      ${compact ? '' : `<td class="tiny muted">${esc(r.last || '—')}</td>`}
    </tr>`).join('')}</tbody></table></div>${compact ? '' : pager(d)}`;
}

function pager(d) {
  const pages = Math.ceil(d.total / d.limit), cur = Math.floor(d.offset / d.limit);
  const win = [];
  for (let i = 0; i < pages; i++) {
    if (i < 2 || i > pages - 2 || Math.abs(i - cur) <= 1) win.push(i);
    else if (win[win.length - 1] !== '…') win.push('…');
  }
  return `<div class="pager">
    <span>Showing ${d.offset + 1}–${Math.min(d.offset + d.limit, d.total)} of ${d.total.toLocaleString()}</span>
    <div class="pages">
      <button data-page="${cur - 1}" ${cur === 0 ? 'disabled' : ''}>Prev</button>
      ${win.map((i) => i === '…' ? '<button disabled>…</button>'
        : `<button data-page="${i}" class="${i === cur ? 'on' : ''}">${i + 1}</button>`).join('')}
      <button data-page="${cur + 1}" ${cur >= pages - 1 ? 'disabled' : ''}>Next</button>
    </div></div>`;
}

function dirQuery(limit, page) {
  const d = state.dir;
  return `/api/directory?q=${encodeURIComponent(d.q)}&band=${encodeURIComponent(d.band)}`
    + `&limit=${limit}&offset=${(page || 0) * limit}`;
}

async function viewMerchants() {
  const d = await api(dirQuery(PAGE_SIZE, state.dir.page));
  return head('Merchants',
    'Every merchant the memory layer has an opinion about, ranked by the probability it would decline them today.',
    `<span class="tiny muted">${d.total.toLocaleString()} on file</span>`)
  + `<div class="card">
      <div class="toolbar">
        <div class="search">${svg('search')}
          <input id="dirq" type="search" placeholder="Search name, domain, or category…"
                 value="${esc(state.dir.q)}"></div>
        <select id="dirband">
          <option value="">All risk levels</option>
          ${d.bands.map((b) => `<option value="${esc(b)}"${state.dir.band === b ? ' selected' : ''}>${esc(b)}</option>`).join('')}
        </select>
        <span class="tiny muted" style="margin-left:auto">Memory score is
          100 &minus; P(bad); it moves when memory changes its mind.</span>
      </div>
      ${dirTable(d)}
    </div>`;
}

/* ------------------------------------------------------- context graph */
async function viewGraph() {
  const p = state.portfolio || await api('/api/portfolio');
  const d = await api(dirQuery(8, 0));
  const rows = d.rows;
  const pick = state.graphId || (rows[0] && rows[0].id);
  const g = pick ? (await api(`/api/brief/${pick}`)).graph : null;
  const who = rows.find((r) => r.id === pick);

  return head('Context graph',
    'The context graph is what turns an isolated application into a merchant with a history. Pick a merchant to see the entities it shares with the rest of the portfolio.',
    `<span class="tiny muted">${p.graph.nodes.toLocaleString()} entities</span>`)
  + `<div class="cols"><div>
      <div class="card"><h3>${who ? esc(who.name) : 'No merchant selected'}
        <span class="hint">corroborating paths, hub nodes suppressed</span></h3>
        ${g ? graphSvg(g) : '<div class="empty">Nothing to draw.</div>'}
        <p class="tiny muted" style="margin:12px 0 0">Shared entities above degree 40 are
          treated as hubs and never carry corroboration — a shared payment processor is not evidence.</p>
      </div></div>
      <div>
      <div class="card"><h3>Highest-risk merchants</h3>
        <div class="rows">${rows.map((r) => `
          <div class="rowitem ${r.id === pick ? 'on' : ''}" data-graph="${esc(r.id)}">
            <div class="sq" style="background:var(--surface-3);color:var(--ink-2)">${esc(initials(r.name))}</div>
            <div class="nm">${esc(r.name)}<span>${esc(title(r.category))}</span></div>
            <span class="chip c-${r.tone}">${pct(r.p_bad)}</span></div>`).join('')}</div></div>
      <div class="card"><h3>Entities by kind</h3>
        <div class="scroll"><table><tbody>
        ${Object.entries(p.graph.by_kind).map(([k, n]) =>
          `<tr><td class="tiny">${esc(title(k))}</td><td class="num">${n.toLocaleString()}</td></tr>`).join('')}
        </tbody></table></div>
        <p class="tiny muted" style="margin:11px 0 0">${p.graph.nodes.toLocaleString()} entities,
          ${p.graph.edges.toLocaleString()} relationships.</p></div>
      </div></div>`;
}
/* Activity lives on the Dashboard as a card. There is deliberately no
   persistent summary strip: once the Dashboard existed, a bar repeating the
   same five numbers on every screen was duplication, and it made simple
   surfaces like Assessment history harder to read. */
const KIND_LABEL = { decision: 'Decision', memory: 'Memory', replay: 'Replay', alert: 'Alert' };

function head(title, sub, right) {
  return `<div class="head"><div><h2>${title}</h2><p>${sub}</p></div>
    <div>${right || ''}</div></div>`;
}

/* ------------------------------------------------------------ portfolio */
async function viewPortfolio() {
  const p = state.portfolio = await api('/api/portfolio');
  renderNav();
  const v = p.vamp;
  const vampPctOfLimit = Math.min(v.ratio / v.above_standard, 1) * 100;
  const vampClass = v.ratio >= v.above_standard ? 'crit'
    : v.ratio >= v.above_standard * 0.8 ? 'warn' : 'ok';

  const kpi = (k, val, note, cls = '', meter = '') =>
    `<div class="kpi ${cls}"><div class="k">${k}</div><div class="v">${val}</div>
      <div class="n">${note}</div>${meter}</div>`;

  return head('Portfolio',
    'Every figure on this page is computed from the synthetic corpus, which is sized to the assumed baseline in section 6.1 of the problem statement.')
    + `<div class="kpis">
      ${kpi('Active merchants', p.approved.toLocaleString(),
        `${p.total_applications.toLocaleString()} applications, ${pct(p.approval_rate, 0)} approved`)}
      ${kpi('Annualised volume', usd(p.annual_volume), 'processed under Acme MIDs')}
      ${kpi('Portfolio VAMP ratio', pct(v.ratio, 3),
        `${v.headroom_pct}% headroom to the ${pct(v.above_standard, 2)} acquirer line`,
        vampClass,
        `<div class="meter"><i class="${vampClass === 'crit' ? 'bad' : vampClass === 'warn' ? 'warn' : 'ok'}" style="width:${vampPctOfLimit}%"></i></div>`)}
      ${kpi('Prepaid exposure', usd(p.prepaid_exposure),
        'owed as service if merchants fail — not fraud', 'warn')}
      ${kpi('Open alerts', p.alert_total,
        `${p.alerts.critical} critical, ${p.alerts.high} high`,
        p.alerts.critical ? 'crit' : '')}
      ${kpi('Review queue', p.queue_size, 'awaiting a decision')}
    </div>`
    + `<div class="card"><h3>Operating point<span class="hint">section 6.2 — assumed, not measured</span></h3>
      <div class="scroll"><table>
        <tr><td>Cost of wrongly approving a bad merchant</td><td class="num">${money(25000)}</td></tr>
        <tr><td>Cost of wrongly declining a good merchant</td><td class="num">${money(4000)}</td></tr>
        <tr><td>Ratio</td><td class="num">${p.cost_ratio} : 1</td></tr>
        <tr><td><strong>Decline threshold</strong> — decline only above this probability of bad</td>
            <td class="num"><strong>${pct(p.threshold)}</strong></td></tr>
      </table></div>
      <p class="tiny muted" style="margin:11px 0 0">We accept roughly six wrongful declines to prevent one wrongful approval. That is deliberately less paranoid than instinct suggests — an MoR that declines everybody has no business.</p>
    </div>`
    + `<div class="card"><h3>Context graph</h3>
      <div class="scroll"><table><thead><tr><th>Entity kind</th><th>Nodes</th></tr></thead><tbody>
      ${Object.entries(p.graph.by_kind).map(([k, n]) =>
        `<tr><td>${esc(k.replace(/_/g, ' '))}</td><td class="num">${n.toLocaleString()}</td></tr>`).join('')}
      </tbody></table></div>
      <p class="tiny muted" style="margin:11px 0 0">${p.graph.nodes.toLocaleString()} nodes, ${p.graph.edges.toLocaleString()} edges.</p>
    </div>`;
}

/* ---------------------------------------------------------------- cases */
function assessmentRows(rows) {
  return rows.map((r) => `<tr class="click" data-open-assess="${esc(r.id)}">
        <td class="tiny muted">${esc((r.at || '').replace('T', ' ').replace('+00:00', ' UTC'))}</td>
        <td><strong>${esc(r.name)}</strong><div class="tiny muted">${esc(r.domain || '')}${r.created ? ' · new' : ''}</div></td>
        <td class="num"><strong>${r.p_bad != null ? pct(r.p_bad) : '—'}</strong></td>
        <td><span class="chip ${r.recommendation === 'decline' ? 'c-bad'
          : r.recommendation === 'escalate' ? 'c-warn'
          : r.recommendation === 'conditions' ? 'c-acc' : 'c-ok'}">${esc(r.headline || r.recommendation || '')}</span></td>
        <td>${r.decision_action
          ? `<span class="chip ${r.decision_action === 'decline' ? 'c-bad' : r.decision_action === 'approve' ? 'c-ok' : 'c-warn'}">${esc(REC_LABEL[r.decision_action] || r.decision_action)}</span>`
          : '<span class="tiny muted">Not recorded</span>'}</td></tr>`).join('');
}

async function viewCases() {
  const [queue, alerts, drift, assessments] = await Promise.all([
    api('/api/queue'), api('/api/alerts'), api('/api/drift'), api('/api/assessments')]);
  state.assessmentIndex = Object.fromEntries((assessments || []).map((r) => [r.id, r]));
  const drifted = new Set(drift.map((d) => d.merchant_id));

  const rows = [
    ...queue.map((q) => ({
      id: q.id, name: q.name, p: q.p_bad, when: q.applied_at,
      kind: 'New application',
      why: q.signal_count ? q.top_signal : 'No signals fired',
      tag: q.recommendation, tagText: q.headline,
    })),
    ...alerts.map((a) => ({
      id: a.merchant_id, name: a.merchant, p: a.p_bad, when: '',
      kind: 'On platform' + (drifted.has(a.merchant_id) ? ' · drifted' : ''),
      why: a.title, tag: a.severity, tagText: a.posture_label,
      exposure: a.exposure,
    })),
  ].sort((a, b) => b.p - a.p);

  const tagClass = (t) => ({ decline: 'c-bad', escalate: 'c-warn', conditions: 'c-acc',
    approve: 'c-ok', critical: 'c-bad', high: 'c-warn', medium: 'c-mute' }[t] || 'c-mute');

  const session = assessments || [];
  const sessionCard = session.length ? `<div class="card"><h3>This session
      <span class="hint">${session.length} assessment${session.length === 1 ? '' : 's'} you ran</span></h3>
      <div class="scroll"><table>
        <thead><tr><th>When</th><th>Merchant</th><th>P(bad)</th><th>Recommendation</th><th>Your decision</th></tr></thead>
        <tbody>${assessmentRows(session)}</tbody></table></div>
      <p class="tiny muted" style="margin:12px 0 0">This is where a Decline or Approve lands.
        Click a row to reopen the brief.</p></div>` : '';

  return head('Evaluations',
    'Your session first — then the engine inbox of cases that already need a human.')
    + sessionCard
    + `<div class="card"><h3>Needs a human
        <span class="hint">queued applications and live alerts — not your session log</span></h3>
      <div class="scroll"><table>
      <thead><tr><th>Merchant</th><th>Why it is here</th><th>P(bad)</th>
        <th>Exposure</th><th></th></tr></thead><tbody>
      ${rows.map((r) => `<tr class="click" data-id="${r.id}">
        <td><strong>${esc(r.name)}</strong><div class="tiny muted">${esc(r.kind)}</div></td>
        <td class="tiny">${esc(r.why)}</td>
        <td class="num">${pct(r.p)}</td>
        <td class="num tiny">${r.exposure ? usd(r.exposure) : '—'}</td>
        <td><span class="chip ${tagClass(r.tag)}">${esc(r.tagText)}</span></td></tr>`).join('')}
      </tbody></table></div>
      <p class="tiny muted" style="margin:12px 0 0">${queue.length} new application${queue.length === 1 ? '' : 's'},
        ${alerts.length} already on the platform, ${drift.length} of them drifted from what we underwrote.
        Click any row to open the case brief.</p>
      <p class="tiny muted" style="margin:6px 0 0">Not shown: ${(state.portfolio.approved || 0).toLocaleString()}
        merchants the system correctly left alone — including
        <strong>${(state.portfolio.real_customers || 0)} named Acme merchants</strong>
        (Mole, Vibe3D, Draftly, Scira AI and others), all clean, none flagged.</p></div>`;
}

/* --------------------------------------------------------------- history */
async function viewHistory() {
  const rows = await api('/api/assessments');
  state.assessmentIndex = Object.fromEntries(rows.map((r) => [r.id, r]));
  if (!rows.length) {
    return head('Assessment history',
      'Every assessment you run — saved locally and kept across restarts.')
      + '<div class="card"><div class="empty">No assessments yet. Run one from Assess a merchant.</div></div>';
  }
  return head('Assessment history',
    'Your recorded Approve / Decline lands in this table — saved locally across restarts. Newest first.')
    + `<div class="card"><div class="scroll"><table>
      <thead><tr><th>When</th><th>Merchant</th><th>P(bad)</th><th>Recommendation</th><th>Your decision</th></tr></thead><tbody>
      ${assessmentRows(rows)}
      </tbody></table></div></div>`;
}

/* ------------------------------------------------------- legacy: queue */
async function viewQueue() {
  const rows = await api('/api/queue');
  if (!rows.length) return head('Review queue', 'Nothing awaiting a decision.');
  return head('Review queue',
    'Applications awaiting a decision, ordered by estimated probability of going bad. The system advises; a human decides.')
    + `<div class="card"><div class="scroll"><table>
      <thead><tr><th>Merchant</th><th>Category</th><th>Applied</th><th>P(bad)</th>
        <th>Recommendation</th><th>Lead signal</th></tr></thead><tbody>
      ${rows.map((r) => `<tr class="click" data-id="${r.id}">
        <td><strong>${esc(r.name)}</strong><div class="tiny muted">${esc(r.domain)} &middot; ${esc(r.country)}</div></td>
        <td class="tiny">${esc(r.category.replace(/_/g, ' '))}</td>
        <td class="num tiny">${esc(r.applied_at)}</td>
        <td class="num"><strong>${pct(r.p_bad)}</strong></td>
        <td><span class="chip ${r.recommendation === 'decline' ? 'c-bad'
          : r.recommendation === 'escalate' ? 'c-warn'
          : r.recommendation === 'conditions' ? 'c-acc' : 'c-ok'}">${esc(r.headline)}</span></td>
        <td class="tiny muted">${esc(r.top_signal)}</td></tr>`).join('')}
      </tbody></table></div></div>`;
}

/* ---------------------------------------------------------------- brief */
function graphSvg(g) {
  if (!g.nodes.length) {
    return `<p class="tiny muted">No graph relationships found. This applicant is not
      connected to anything we have already judged — which for a content-risk case is
      the expected result.</p>`;
  }
  const applicant = g.nodes.find((n) => n.role === 'applicant');
  const bridges = g.nodes.filter((n) => n.role === 'bridge');
  const others = g.nodes.filter((n) => n.role === 'related_merchant');
  const H = Math.max(150, Math.max(bridges.length, others.length) * 56 + 40);
  const W = 720;
  const col = (arr, x) => arr.map((n, i) => ({
    ...n, x, y: (H / (arr.length + 1)) * (i + 1),
  }));
  const pos = {};
  [...col([applicant].filter(Boolean), 92), ...col(bridges, 360), ...col(others, 628)]
    .forEach((n) => pos[n.id] = n);

  // Several routes converge on the same merchant, so midpoint labels collide.
  // Stagger each label vertically by its rank among edges sharing a destination.
  const drawable = g.edges.filter((e) => pos[e.src] && pos[e.dst]);
  const rank = {};
  drawable.forEach((e) => {
    rank[e.dst] = rank[e.dst] || [];
    rank[e.dst].push(e);
  });
  const offsetOf = (e) => {
    const group = rank[e.dst];
    const i = group.indexOf(e);
    return (i - (group.length - 1) / 2) * 14;
  };

  const edges = drawable.map((e) => {
    const a = pos[e.src], b = pos[e.dst];
    const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2 - 6 + offsetOf(e);
    const w = e.label.length * 5.6;
    return `<line x1="${a.x + 62}" y1="${a.y}" x2="${b.x - 62}" y2="${b.y}"
      stroke="var(--accent)" stroke-opacity="${0.28 + e.weight * 0.5}" stroke-width="1.5"/>
      <rect x="${mx - w / 2}" y="${my - 9}" width="${w}" height="12" rx="2"
        fill="var(--surface-2)"/>
      <text x="${mx}" y="${my}" text-anchor="middle"
        font-family="ui-monospace,Menlo,monospace" font-size="9.5"
        fill="var(--muted)">${esc(e.label)}</text>`;
  }).join('');

  const nodes = Object.values(pos).map((n) => {
    const isM = n.kind === 'merchant';
    const stroke = n.role === 'related_merchant' ? 'var(--bad)'
      : n.role === 'applicant' ? 'var(--accent)' : 'var(--rule-2)';
    const label = n.label.length > 20 ? n.label.slice(0, 19) + '…' : n.label;
    return `<rect x="${n.x - 62}" y="${n.y - 17}" width="124" height="34" rx="4"
        fill="var(--surface)" stroke="${stroke}" stroke-width="${isM ? 1.6 : 1}"/>
      <text x="${n.x}" y="${n.y - 2}" text-anchor="middle" font-size="11"
        fill="var(--ink)">${esc(label)}</text>
      <text x="${n.x}" y="${n.y + 10}" text-anchor="middle"
        font-family="ui-monospace,Menlo,monospace" font-size="8"
        fill="var(--muted)">${esc(n.kind.replace(/_/g, ' ').toUpperCase())}</text>`;
  }).join('');

  return `<svg class="graph" viewBox="0 0 ${W} ${H}" role="img"
    aria-label="Context graph neighbourhood for this applicant">${edges}${nodes}</svg>`;
}

async function viewBrief(id) {
  const b = await api('/api/brief/' + id);
  const m = b.merchant, d = b.decision;
  const tierChip = { prohibited: 'c-bad', restricted: 'c-warn', accepted: 'c-ok' }[b.policy.tier];

  const signals = b.signals.length ? b.signals.map((s) => `
    <div class="sig p-${esc(s.posture)}">
      <div class="t"><span>${esc(s.title)}</span><span class="lr">LR ${s.lr}</span></div>
      <div class="d">${esc(s.detail)}</div>
      <div class="e">${esc(s.posture_label)} &middot; ${s.evidence.map(esc).join(' &middot; ')}</div>
    </div>`).join('') : '<p class="tiny muted">No signals fired.</p>';

  const precedent = b.precedent.map((p) => `<tr>
      <td><strong>${esc(p.name)}</strong><div class="tiny muted">${esc(p.pitch.slice(0, 74))}</div></td>
      <td class="num tiny">${p.similarity.toFixed(2)}</td>
      <td><span class="chip ${p.went_bad ? 'c-bad' : p.status === 'declined' ? 'c-warn' : 'c-ok'}">${
        p.went_bad ? 'went bad' : p.status === 'declined' ? 'declined' : 'clean'}</span>${
        p.went_bad && p.status !== 'terminated' ? '<div class="tiny muted">still active</div>' : ''}</td>
      <td class="tiny muted">${esc((p.shared_terms || []).join(', '))}</td></tr>`).join('');

  const memories = b.memories.length ? b.memories.map((x) => `
    <div class="sig p-memory"><div class="t"><span>${esc(x.kind)} memory</span>
      <span class="lr">sim ${x.similarity.toFixed(2)}</span></div>
      <div class="d">${esc(x.text)}</div>
      <div class="e">${esc(x.source)} &middot; confidence ${x.confidence}</div></div>`).join('')
    : '<p class="tiny muted">Nothing in memory matches this applicant.</p>';

  const contribs = d.contributions.map((c) => `<div class="row">
      <span>${esc(c.title.slice(0, 46))}</span>
      <span>&times;${c.applied_lr} &nbsp;&rarr;&nbsp; ${pct(c.p_after)}</span></div>`).join('');

  const decidable = m.status === 'pending';

  return head(esc(m.name) + (m.real ? ' <span class="real">Acme merchant</span>' : ''),
    `${esc(m.domain)} &middot; ${esc(m.country)} &middot; applied ${esc(m.applied_at)} &middot;
     <span class="chip ${tierChip}">${esc(b.policy.tier)}</span>` +
     (m.real ? ' <span class="tiny muted">&mdash; named Acme merchant; product description from their case study, operating figures illustrative</span>' : ''),
    `<button class="btn ghost small" id="back">&larr; Back to queue</button>`)
  + `<div class="brief"><div>
      <div class="card"><h3>Evidence<span class="hint">findings first, recommendation last</span></h3>
        <p class="tiny muted" style="margin:-4px 0 12px">${esc(m.pitch)}</p>
        ${signals}</div>
      <div class="card"><h3>Context graph<span class="hint">who this applicant is connected to</span></h3>
        ${graphSvg(b.graph)}
        ${b.related.length ? `<div class="scroll" style="margin-top:12px"><table>
          <thead><tr><th>Related merchant</th><th>Status</th><th>Score</th><th>Routes</th></tr></thead><tbody>
          ${b.related.map((r) => `<tr><td><strong>${esc(r.name)}</strong></td>
            <td><span class="chip ${r.status === 'terminated' ? 'c-bad' : 'c-mute'}">${esc(r.status)}</span></td>
            <td class="num">${r.score.toFixed(3)}</td>
            <td class="tiny mono muted">${r.routes.map(esc).join('<br>')}</td></tr>`).join('')}
          </tbody></table></div>` : ''}</div>
      <div class="card"><h3>Precedent<span class="hint">closest decided cases and how they turned out</span></h3>
        <div class="scroll"><table><thead><tr><th>Case</th><th>Sim</th><th>Outcome</th><th>Matched on</th></tr></thead>
        <tbody>${precedent}</tbody></table></div>
        <p class="tiny muted" style="margin:11px 0 0">${esc(d.precedent_note)}</p></div>
      <div class="card"><h3>Memory consulted</h3>${memories}</div>
    </div><div>
      <div class="verdict ${esc(d.recommendation)}">
        <div class="k mono tiny muted">ESTIMATED P(BAD)</div>
        <div class="p">${pct(d.p_bad)}</div>
        <div class="h">${esc(d.headline)}</div>
        <div class="sub">Threshold is ${pct(d.threshold)}. Expected cost of approving
          <strong>${money(d.expected_cost_approve)}</strong> against
          <strong>${money(d.expected_cost_decline)}</strong> for declining.</div>
        <div class="math"><div class="row"><span>Base rate</span><span>${pct(d.prior)}</span></div>
          ${contribs}</div></div>
      ${decidable ? `<div class="card"><h3>Your decision</h3>
        <textarea id="rationale" placeholder="Two lines on why. This is captured as memory and is what the learning loop runs on."></textarea>
        <div class="actions">
          <button class="btn" data-act="approve">Approve</button>
          <button class="btn ghost" data-act="conditions">With conditions</button>
          <button class="btn danger" data-act="decline">Decline</button>
        </div></div>`
        : `<div class="card"><h3>Decision on file</h3>
           <p class="tiny"><span class="chip c-mute">${esc(m.status)}</span>
           ${m.decided_at ? ` ${esc(m.decided_at)} by ${esc(m.decided_by || '—')}` : ''}</p>
           <p class="tiny muted" style="margin:8px 0 0">${esc(m.rationale || 'No rationale recorded.')}</p></div>`}
      <div class="card"><h3>Application facts</h3><div class="scroll"><table>
        <tr><td>Domain age</td><td class="num">${m.domain_age_days} days</td></tr>
        <tr><td>Registrar / NS</td><td class="tiny">${esc(m.registrar)} / ${esc(m.nameserver)}</td></tr>
        <tr><td>Payout</td><td class="tiny">${esc(m.payout_iban)}<br>${esc(m.payout_holder)}</td></tr>
        <tr><td>Fulfilment</td><td class="tiny">${m.fulfilment.map(esc).join(', ')}</td></tr>
        ${m.forecast_monthly ? `<tr><td>Forecast / actual</td><td class="num tiny">${money(m.forecast_monthly)} / ${money(m.monthly_volume)}</td></tr>` : ''}
        ${m.refund_rate ? `<tr><td>Refund rate</td><td class="num">${pct(m.refund_rate)}</td></tr>` : ''}
        ${m.prepaid_balance ? `<tr><td>Prepaid balance</td><td class="num">${money(m.prepaid_balance)}</td></tr>` : ''}
      </table></div></div>
    </div></div>`;
}

/* --------------------------------------------------------------- alerts */
async function viewAlerts() {
  const rows = await api('/api/alerts');
  const by = { critical: [], high: [], medium: [] };
  rows.forEach((r) => by[r.severity].push(r));
  return head('Alerts',
    'Merchants already on the platform, grouped by what kind of trouble they are in. Two of these four postures were invisible to the original three cases.')
    + ['critical', 'high', 'medium'].map((sev) => !by[sev].length ? '' : `
      <div class="card"><h3>${sev[0].toUpperCase() + sev.slice(1)}
        <span class="hint">${by[sev].length} merchant${by[sev].length === 1 ? '' : 's'}</span></h3>
      <div class="scroll"><table><thead><tr><th>Merchant</th><th>Posture</th>
        <th>What is happening</th><th>P(bad)</th><th>Exposure</th></tr></thead><tbody>
      ${by[sev].map((a) => `<tr class="click" data-id="${a.merchant_id}">
        <td><strong>${esc(a.merchant)}</strong></td>
        <td><span class="chip ${a.posture === 'attacked' ? 'c-warn'
          : a.posture === 'failing' ? 'c-acc' : 'c-bad'}">${esc(a.posture_label)}</span></td>
        <td>${esc(a.title)}<div class="tiny muted">${esc(a.detail.slice(0, 108))}</div></td>
        <td class="num">${pct(a.p_bad)}</td>
        <td class="num">${usd(a.exposure)}</td></tr>`).join('')}
      </tbody></table></div></div>`).join('');
}

/* ---------------------------------------------------------------- drift */
async function viewDrift() {
  const rows = await api('/api/drift');
  return head('Drift monitor',
    'Continuous reconciliation of what each merchant told us they sell against what they are observed selling. This is the only way Case B is ever caught before the chargeback.')
    + (!rows.length ? '<div class="card"><div class="empty">No divergence detected.</div></div>'
      : `<div class="card"><div class="scroll"><table>
      <thead><tr><th>Merchant</th><th>claims_to_sell</th><th>observed_selling</th>
        <th>Seen</th><th>Volume</th><th></th></tr></thead><tbody>
      ${rows.map((r) => `<tr class="click" data-id="${r.merchant_id}">
        <td><strong>${esc(r.merchant)}</strong></td>
        <td class="tiny">${esc(r.claims_to_sell)}<div class="mono muted">${esc(r.claimed_category)}</div></td>
        <td class="tiny">${esc(r.observed_selling)}<div class="mono muted">${esc(r.observed_category)}</div></td>
        <td class="num tiny">${esc(r.last_observed_at || '—')}</td>
        <td class="num">${usd(r.monthly_volume)}</td>
        <td>${r.prohibited_now ? '<span class="chip c-bad">now prohibited</span>'
          : '<span class="chip c-warn">diverged</span>'}</td></tr>`).join('')}
      </tbody></table></div></div>`);
}

/* --------------------------------------------------------------- memory */
async function viewMemory() {
  const m = await api('/api/memory');
  const c = m.counts;
  const chip = { ADD: 'c-ok', UPDATE: 'c-acc', INVALIDATE: 'c-bad', 'NO-OP': 'c-mute', DISPUTED: 'c-warn' };
  return head('Memory',
    'Every case and every correction is reconciled against what memory already holds — add, update, invalidate or no-op. Reconciled, not appended.')
    + `<div class="kpis">
      <div class="kpi"><div class="k">Active</div><div class="v">${c.active}</div><div class="n">records in force</div></div>
      <div class="kpi"><div class="k">Superseded</div><div class="v">${c.superseded}</div><div class="n">refined by a later fact</div></div>
      <div class="kpi"><div class="k">Invalidated</div><div class="v">${c.invalidated}</div><div class="n">contradicted, kept for audit</div></div>
      <div class="kpi warn"><div class="k">Disputed</div><div class="v">${c.disputed || 0}</div><div class="n">conflict flagged for a human</div></div>
      <div class="kpi"><div class="k">Awaiting gate</div><div class="v">${c.pending_gate}</div><div class="n">not yet influencing decisions</div></div>
    </div>`
    + `<div class="card"><h3>Reconciliation log<span class="hint">most recent first</span></h3>
      <div class="scroll"><table><thead><tr><th>Action</th><th>Statement</th><th>Why</th><th>Sim</th></tr></thead><tbody>
      ${m.log.map((l) => `<tr><td><span class="chip ${chip[l.action] || 'c-mute'}">${esc(l.action)}</span></td>
        <td class="tiny">${esc(l.memory.text.slice(0, 108))}</td>
        <td class="tiny muted">${esc(l.reason)}</td>
        <td class="num tiny">${l.similarity.toFixed(2)}</td></tr>`).join('')}
      </tbody></table></div></div>`
    + `<div class="card"><h3>Records</h3><div class="scroll"><table>
      <thead><tr><th>Kind</th><th>Statement</th><th>Category</th><th>Conf</th><th>Source</th><th>Status</th></tr></thead><tbody>
      ${m.records.slice(0, 60).map((r) => `<tr>
        <td><span class="chip ${r.kind === 'semantic' ? 'c-acc' : r.kind === 'procedural' ? 'c-warn' : 'c-mute'}">${esc(r.kind)}</span></td>
        <td class="tiny">${esc(r.text.slice(0, 120))}${r.predicate ? `<div class="mono muted">predicate-matched</div>` : ''}</td>
        <td class="tiny muted">${esc((r.category || '—').replace(/_/g, ' '))}</td>
        <td class="num tiny">${r.confidence}</td>
        <td class="tiny muted">${esc(r.source.slice(0, 34))}</td>
        <td><span class="chip ${r.status === 'active' ? (r.promoted ? 'c-ok' : 'c-warn') : 'c-mute'}">${r.status === 'active' && !r.promoted ? 'awaiting gate' : esc(r.status)}</span></td>
      </tr>`).join('')}
      </tbody></table></div></div>`
    + await replaySection();
}

/* --------------------------------------------------------------- replay */
async function replaySection() {
  const [incidents, history] = await Promise.all([
    api('/api/incidents'), api('/api/gate-history')]);
  const seen = new Set(history.map((h) => h.incident.id));
  const options = incidents.filter((i) => !seen.has(i.id)).slice(0, 24);

  return `<div class="card"><h3>Is it improving?
      <span class="hint">confirm an outcome — the system distils a pattern, replays every past decision with and without it, and promotes it only if it catches more without wrongly flagging more</span></h3>
      <p class="tiny muted" style="margin:-4px 0 11px">Pick an incident. This is the slow learning path: labels arrive months after the decision they judge.</p>
      <div class="actions">
        <select id="incident" style="flex:1;min-width:280px;padding:8px;border-radius:5px;border:1px solid var(--rule-2);background:var(--surface);color:var(--ink);font:inherit;font-size:13px">
          ${options.map((i) => `<option value="${i.id}">${esc(i.name)} — ${esc((i.category || '').replace(/_/g, ' '))}</option>`).join('')}
        </select>
        <button class="btn" id="run" ${options.length ? '' : 'disabled'}>Ingest &amp; replay</button>
      </div></div>`
    + (history.length ? history.slice().reverse().map((h) => `
      <div class="card"><h3>${esc(h.incident.name)}
        <span class="hint">${esc((h.incident.category || '').replace(/_/g, ' '))}</span></h3>
        <p class="tiny muted" style="margin:-4px 0 10px">${esc(h.incident.note)}</p>
        <div class="sig p-memory"><div class="t"><span>Distilled pattern</span>
          <span class="lr">confidence ${h.candidate.confidence}</span></div>
          <div class="d">${esc(h.candidate.text)}</div>
          ${h.candidate.predicate ? `<div class="e">predicate: ${esc(JSON.stringify(h.candidate.predicate.all))}</div>` : ''}
        </div>
        <div class="gate">
          <div class="box"><div class="lbl">Before — without this memory</div>
            <div class="big">${h.before.caught} / ${h.before.bad_total}</div>
            <div class="tiny muted">caught &middot; ${h.before.false_flags} wrongly flagged of ${h.before.clean_total}</div></div>
          <div class="arrow">&rarr;</div>
          <div class="box after"><div class="lbl">After — with it promoted</div>
            <div class="big">${h.after.caught} / ${h.after.bad_total}</div>
            <div class="tiny muted">caught &middot; ${h.after.false_flags} wrongly flagged of ${h.after.clean_total}</div></div>
        </div>
        <p style="margin:6px 0 0"><span class="chip ${h.promoted ? 'c-ok' : 'c-warn'}">${h.promoted ? 'promoted' : 'held back'}</span>
          <span class="tiny" style="margin-left:8px">${esc(h.verdict)}</span></p>
        <p class="tiny muted" style="margin:8px 0 0">Delta: ${h.caught_delta >= 0 ? '+' : ''}${h.caught_delta} caught,
          ${h.false_flag_delta >= 0 ? '+' : ''}${h.false_flag_delta} wrongly flagged.
          This delta is the anti-fragility claim: it is what "the system gets stronger from an incident" means as a number.</p>
      </div>`).join('')
      : `<div class="card"><div class="empty">No incidents ingested yet. Run one above to see the gate work.</div></div>`);
}
function signalCards(signals, empty) {
  if (!signals || !signals.length) return `<p class="tiny muted">${esc(empty)}</p>`;
  return signals.map((s) => `
    <div class="sig p-${esc(s.posture)}">
      <div class="t"><span>${esc(s.title)}</span><span class="lr">LR ${s.lr}</span></div>
      <div class="d">${esc(s.detail)}</div>
      <div class="e">${esc(s.posture_label)} &middot; ${(s.evidence || []).map(esc).join(' &middot; ')}</div>
    </div>`).join('');
}

function memoryCards(memories, empty) {
  if (!memories || !memories.length) return `<p class="tiny muted">${esc(empty)}</p>`;
  return memories.map((x) => `
    <div class="sig p-memory"><div class="t"><span>${esc(x.kind)} memory</span>
      <span class="lr">sim ${x.similarity.toFixed(2)}</span></div>
      <div class="d">${esc(x.text)}</div>
      <div class="e">${esc(x.source)} &middot; confidence ${x.confidence}</div></div>`).join('');
}

const REC_LABEL = {
  approve: 'Approve', conditions: 'Approve with conditions',
  escalate: 'Review', decline: 'Decline',
};

const ASSESS_CATS = [
  ['saas_ai_digital', 'SaaS / AI or Digital products'],
  ['edtech', 'Edtech'],
  ['services', 'Services'],
  ['financial_services', 'Financial services'],
  ['physical_products', 'Physical products'],
  ['gaming', 'Gaming'],
  ['marketplace', 'Marketplace'],
  ['others', 'Others'],
];
const ASSESS_TAX = [
  ['saas', 'SaaS'], ['digital_products', 'Digital products'],
  ['ebook', 'E-Book'], ['edtech', 'Edtech'],
];
const ISO2 = (`AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ
BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY
CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM
GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE
KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML
MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF
PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN
SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ
VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW`).split(/\s+/);
const regionNames = (typeof Intl !== 'undefined' && Intl.DisplayNames)
  ? new Intl.DisplayNames(['en'], { type: 'region' }) : null;
function flagEmoji(iso) {
  const code = String(iso || '').toUpperCase();
  if (!/^[A-Z]{2}$/.test(code)) return '';
  return String.fromCodePoint(...[...code].map((c) => 127397 + c.charCodeAt(0)));
}
function countryName(iso) {
  const code = String(iso || '').toUpperCase();
  try { return (regionNames && regionNames.of(code)) || code; } catch { return code; }
}
function countryOptions(selected) {
  return ISO2.map((iso) => ({ iso, name: countryName(iso) }))
    .sort((a, b) => a.name.localeCompare(b.name))
    .map(({ iso, name }) => {
      const sel = iso === selected ? ' selected' : '';
      return `<option value="${iso}"${sel}>${esc(flagEmoji(iso) + ' ' + name)}</option>`;
    }).join('');
}
const ASSESS_REFERRAL = [
  'Twitter/X', 'LinkedIn', 'Reddit', 'Google Search', 'ChatGPT',
  'Perplexity', 'YouTube', 'Instagram', 'TikTok', 'RedNote', 'Referred by someone',
];
const ASSESS_ENTITLEMENTS = [
  ['telegram', 'Telegram'], ['discord', 'Discord'], ['github', 'GitHub'],
  ['license', 'License key'], ['files', 'Digital files'],
  ['notion', 'Notion'], ['framer', 'Framer'],
];
const APP_STAGE = {
  disclaimer: 'At disclaimer', signup: 'Signup',
  product_form_pending: 'Product form in', kyc_pending: 'KYC pending',
  on_platform: 'On platform',
};
const APP_KYC = {
  not_started: 'KYC not started', pending: 'KYC pending', approved: 'KYC approved',
};
const req = '<span class="req" aria-hidden="true">*</span>';

async function viewAssess() {
  if (state.assessResult) return viewAssessResult(state.assessResult);
  if (!state.applications) {
    try { state.applications = await api('/api/applications'); }
    catch { state.applications = []; }
  }
  return viewAssessForm();
}

function viewAssessForm() {
  const mode = state.assessMode || 'import';
  const draft = state.assessDraft;
  const selectedCountry = (draft && draft.country) || '';
  const seg = `<div class="seg" role="tablist" aria-label="How to load merchant data">
      <button type="button" data-assess-mode="import" class="${mode === 'import' ? 'on' : ''}">Import from Acme</button>
      <button type="button" data-assess-mode="manual" class="${mode === 'manual' ? 'on' : ''}">Fill manually</button>
    </div>
    <p class="tiny muted" style="margin:-8px 0 16px">When a merchant signs up, adds a product, and starts KYC, that packet lands here.
      Import it so you are not retyping what they already submitted. Manual fill is for cases that are not in Acme yet.</p>`;

  if (mode === 'import') {
    const rows = state.applications || [];
    const inbox = rows.length ? `<div class="inbox">${rows.map((a) => `
        <div class="inbox-row">
          <div class="flag" aria-hidden="true">${esc(flagEmoji(a.country))}</div>
          <div class="nm">
            <strong>${esc(a.name)}</strong>
            <div class="tiny muted">${esc(countryName(a.country))} · ${esc(title(a.signup_category))}
              · ${esc(APP_STAGE[a.stage] || a.stage)} · ${esc(APP_KYC[a.kyc] || a.kyc)}</div>
            <div class="tiny muted">${esc(a.note || '')}</div>
          </div>
          <button type="button" class="btn small" data-import="${esc(a.id)}">Import</button>
        </div>`).join('')}</div>`
      : '<p class="empty">No inbound packets in this demo inbox.</p>';
    return head('Assess a merchant',
      'Pull the merchant’s Acme packet, review it, then run the same engine.')
      + `<div class="card assess-card"><h3>Inbound from Acme<span class="hint">signup + product + KYC</span></h3>
        ${seg}${inbox}
        <p class="tiny muted">Demo inbox stands in for the live webhook. In production this is the same JSON the merchant already posted to Acme.</p>
      </div>`;
  }

  const banner = draft && draft.application_id ? `<div class="import-banner">
      <div><strong>Imported from Acme</strong>
        <div class="tiny muted">${esc((draft._meta && draft._meta.source) || 'acme.signup')}
          · ${esc(APP_STAGE[(draft._meta && draft._meta.stage)] || '')}
          · ${esc((draft._meta && draft._meta.note) || 'Merchant-submitted packet — edit before you run if something looks off.')}</div></div>
      <button type="button" class="btn ghost small" data-assess-mode="import">Inbox</button>
    </div>` : '';

  return head('Assess a merchant',
    'Same packet Acme collects at signup and Add product. Policy first, then web, graph, and memory. The system recommends; you decide.')
  + `<div class="card assess-card">
      ${seg}${banner}
      <h3>Signup</h3>
      <p class="tiny muted" style="margin:-4px 0 14px">Fields from the public registration form. Name is enough to reopen someone already on file.</p>
      <form id="assess-form">
        <div class="fields">
          <div class="field"><label for="afull">Full name ${req}</label>
            <input id="afull" name="full_name" autocomplete="off" placeholder="Operator / founder"></div>
          <div class="field"><label for="aname">Business name ${req}</label>
            <input id="aname" name="name" required autocomplete="off"
                   placeholder="e.g. Lumen Labs"></div>
          <div class="field span"><label for="aurl">Website URL ${req}</label>
            <input id="aurl" name="website" autocomplete="off" placeholder="https://"></div>
          <div class="field"><label for="acat">Product category ${req}</label>
            <select id="acat" name="signup_category">${ASSESS_CATS.map(([v, l]) =>
              `<option value="${v}">${esc(l)}</option>`).join('')}</select></div>
          <div class="field"><label for="actry">Where are you located? ${req}</label>
            <select id="actry" name="country"><option value="">Select...</option>
              ${countryOptions(selectedCountry)}</select></div>
          <div class="field"><label for="aentity">Individual or registered entity</label>
            <select id="aentity" name="entity_type">
              <option value="individual">Individual</option>
              <option value="registered" selected>Registered entity</option>
            </select></div>
          <div class="field"><label for="aref">Where did you hear about us? ${req}</label>
            <select id="aref" name="referral"><option value="">Select referral source</option>
              ${ASSESS_REFERRAL.map((r) => `<option>${esc(r)}</option>`).join('')}</select></div>
          <div class="field span"><label for="apur">How can we make monetization simpler for you?</label>
            <textarea id="apur" name="purpose" placeholder="What they sell, and how they charge."></textarea></div>
        </div>
        <h3 style="margin:22px 0 8px">Add product</h3>
        <p class="tiny muted" style="margin:0 0 14px">Catalogue fields from the dashboard form. Tax category and fulfillment are how misclassification shows up.</p>
        <div class="fields">
          <div class="field"><label for="aprod">Product name ${req}</label>
            <input id="aprod" name="product_name" placeholder="Eg: Framer Template"></div>
          <div class="field"><label for="atax">Tax category ${req}</label>
            <select id="atax" name="tax_category">${ASSESS_TAX.map(([v, l]) =>
              `<option value="${v}">${esc(l)}</option>`).join('')}</select></div>
          <div class="field"><label for="aptype">Pricing type</label>
            <select id="aptype" name="pricing_type">
              <option value="one_time">One time</option>
              <option value="subscription">Subscription</option>
              <option value="usage">Usage based</option>
            </select></div>
          <div class="field"><label for="aprice">Price (USD) ${req}</label>
            <input id="aprice" name="price" type="number" min="0" step="0.01" placeholder="0"></div>
          <div class="field span"><label>Entitlements — how access is delivered</label>
            <div class="checks">${ASSESS_ENTITLEMENTS.map(([v, l]) =>
              `<label><input type="checkbox" name="ent" value="${v}"> ${esc(l)}</label>`).join('')}</div></div>
        </div>
        <div class="actions">
          <button class="btn-primary" id="arun" type="submit">${svg('shield')} Run Assessment</button>
        </div>
        <p class="err tiny" id="aerr" hidden></p>
      </form></div>`;
}

function viewAssessResult(b) {
  const m = b.merchant, d = b.decision;
  const rec = d.recommendation;
  const recText = REC_LABEL[rec] || d.headline;
  const relatedEmpty = '<p class="tiny muted">No related entities found.</p>';
  const confirm = b.decisionRecorded;
  const decided = (m.status && m.status !== 'pending') || !!confirm;
  const toneChip = { ok: 'ok', warn: 'warn', high: 'high', bad: 'bad' }[b.risk_band_tone] || 'mute';

  return head(esc(m.name) + (m.real ? ' <span class="real">Acme merchant</span>' : ''),
    `${esc(m.domain)} · ${esc(m.country)} · ${esc(title(m.category_claimed))}`
    + (b.created ? ' · <span class="chip c-mute">new application</span>' : '')
    + ` · <span class="chip c-mute">${esc(m.status)}</span>`,
    `<button class="btn ghost small" id="assess-back">${
      state.assessFrom === 'history' ? '← Assessment history'
      : state.assessFrom === 'cases' ? '← Evaluations'
      : 'New assessment'}</button>`)
  + `<div class="brief"><div>
      <div class="verdict rec-card ${esc(rec)}">
        <div class="rec-hero">
          <div class="rec-call">
            <div class="mono tiny muted">SYSTEM RECOMMENDATION</div>
            <div class="rec-title">
              <div class="h">${esc(recText)}</div>
              <span class="chip c-${esc(toneChip)}">${esc(b.risk_band)}</span>
            </div>
            <p class="rec-vs">${pct(d.p_bad)} probability of going bad</p>
          </div>
        </div>
        ${pBadMeter(d.p_bad, d.threshold, b.risk_band_tone)}
        ${webCard(b.web)}
        ${recWhy(b, d)}
      </div>

      <div class="card"><h3>Risk signals<span class="hint">${(b.signals || []).length} fired</span></h3>
        ${signalCards(b.signals, 'No signals fired.')}</div>

      <div class="card"><h3>Relevant memory<span class="hint">what the platform already believes</span></h3>
        ${memoryCards(b.memories, 'No relevant historical memory found.')}
        ${b.precedent && b.precedent.length ? `<div class="scroll" style="margin-top:12px"><table>
          <thead><tr><th>Closest cases</th><th>Sim</th><th>Outcome</th></tr></thead><tbody>
          ${b.precedent.map((p) => `<tr>
            <td><strong>${esc(p.name)}</strong><div class="tiny muted">${esc((p.outcome || p.status).slice(0, 90))}</div></td>
            <td class="num tiny">${p.similarity.toFixed(2)}</td>
            <td><span class="chip ${p.went_bad ? 'c-bad' : p.status === 'declined' ? 'c-warn' : 'c-ok'}">${
              p.went_bad ? 'went bad' : esc(p.status)}</span></td></tr>`).join('')}
          </tbody></table></div>
          <p class="tiny muted" style="margin:11px 0 0">${esc(d.precedent_note)}</p>`
          : `<p class="tiny muted" style="margin:10px 0 0">${esc(d.precedent_note || 'No comparable historical cases retrieved.')}</p>`}
      </div>

      <div class="card"><h3>Relationship / graph context</h3>
        ${b.graph && b.graph.nodes && b.graph.nodes.length ? graphSvg(b.graph) : relatedEmpty}
        ${b.related && b.related.length ? `<div class="scroll" style="margin-top:12px"><table>
          <thead><tr><th>Related merchant</th><th>Status</th><th>Routes</th></tr></thead><tbody>
          ${b.related.map((r) => `<tr><td><strong>${esc(r.name)}</strong></td>
            <td><span class="chip ${r.status === 'terminated' ? 'c-bad' : 'c-mute'}">${esc(r.status)}</span></td>
            <td class="tiny mono muted">${r.routes.map(esc).join('<br>')}</td></tr>`).join('')}
          </tbody></table></div>` : ''}</div>
    </div><div>
      ${confirm ? `<div class="card"><h3>Analyst decision recorded</h3>
        <p><span class="chip ${confirm.action === 'decline' ? 'c-bad' : confirm.action === 'approve' ? 'c-ok' : 'c-warn'}">${esc(REC_LABEL[confirm.action] || confirm.action)}</span>
          ${confirm.reconciliation && confirm.reconciliation !== 'on file'
            ? `Memory reconciled: ${esc(confirm.reconciliation)}.`
            : 'On file — this is what memory learned from.'}</p>
        <p class="tiny muted" style="margin:8px 0 12px">${esc(confirm.rationale)}</p>
        <div class="actions">
          <button class="btn" id="assess-to-history">Assessment history</button>
          <button class="btn ghost" id="assess-change">Change decision</button>
        </div></div>`
      : `<div class="card"><h3>Analyst decision</h3>
        <p class="tiny muted" style="margin:-4px 0 12px">The system recommended <strong>${esc(recText)}</strong>.
          Your decision is recorded through the existing decision path and is what memory learns from.</p>
        <textarea id="assess-rationale" placeholder="Required. Two lines on why — this is captured as memory."></textarea>
        <p class="err tiny" id="aerr" hidden></p>
        <div class="actions" id="assess-actions">
          <button class="btn" data-assess-act="approve">Approve</button>
          <button class="btn ghost" data-assess-act="escalate">Review</button>
          <button class="btn danger" data-assess-act="decline">Decline</button>
        </div>
        ${decided ? `<p class="tiny muted" style="margin:10px 0 0">A decision is already on file
          (${esc(m.status)}${m.decided_at ? `, ${esc(m.decided_at)}` : ''}). Submitting overwrites it.</p>` : ''}
        </div>`}
    </div></div>`;
}

/* ----------------------------------------------------------------- glue */
const RENDER = {
  homepage: viewHomepage, merchants: viewMerchants, cases: viewCases,
  memory: viewMemory, graph: viewGraph, alerts: viewAlerts,
  history: viewHistory, assess: viewAssess,
  // reachable by link, not tabs
  portfolio: viewPortfolio, queue: viewQueue, drift: viewDrift,
};

async function render() {
  syncTopbar();
  const main = $('#main');
  main.innerHTML = '<div class="page"><div class="empty"><span class="spinner"></span>Loading…</div></div>';
  try {
    const home = !state.briefId && state.view === 'homepage';
    main.innerHTML = `<div class="page${home ? ' homepage' : ''}">` + (state.briefId
      ? await viewBrief(state.briefId)
      : await RENDER[state.view]()) + '</div>';
  } catch (e) {
    main.innerHTML = `<div class="page"><div class="card"><div class="empty">Could not load this view.<br>
      <span class="mono">${esc(e.message)}</span></div></div></div>`;
    return;
  }
  wire();
  window.scrollTo({ top: 0 });
  if ($('#dirmount')) loadDirMount();
}

/* The Homepage embeds the top of the directory; it loads after paint so the
   rest of the page is not held up by a second request. */
async function loadDirMount() {
  const mount = $('#dirmount');
  try {
    mount.innerHTML = dirTable(await api(dirQuery(3, 0)), true);
    mount.querySelectorAll('tr.click').forEach((tr) =>
      tr.onclick = () => { state.briefId = tr.dataset.id; render(); });
  } catch { mount.innerHTML = '<div class="empty">Directory unavailable.</div>'; }
}

const ASSESS_STEPS = [
  'Looking the company up on the public web',
  'Checking merchant profile',
  'Retrieving relevant memory',
  'Evaluating risk signals',
  'Building assessment',
];

function fillAssessForm(p) {
  if (!p || !$('#assess-form')) return;
  const set = (id, v) => {
    const el = $(id);
    if (!el || v == null || v === '') return;
    el.value = v;
  };
  set('#afull', p.full_name);
  set('#aname', p.name);
  set('#aurl', p.website);
  set('#acat', p.signup_category || p.category);
  set('#actry', p.country);
  set('#aentity', p.entity_type);
  set('#aref', p.referral);
  set('#apur', p.purpose);
  set('#aprod', p.product_name);
  set('#atax', p.tax_category);
  set('#aptype', p.pricing_type);
  if (p.price != null && p.price !== '') set('#aprice', p.price);
  (p.entitlements || []).forEach((v) => {
    const el = document.querySelector(`input[name="ent"][value="${v}"]`);
    if (el) el.checked = true;
  });
}

function showAssessError(msg) {
  const el = $('#aerr');
  if (!el) { toast(msg); return; }
  el.hidden = false;
  el.textContent = msg;
}

function wireAssess() {
  const back = $('#assess-back');
  if (back) back.onclick = () => {
    const from = state.assessFrom;
    state.assessResult = null;
    state.assessFrom = null;
    go(from === 'history' || from === 'cases' ? from : 'assess');
  };
  const anew = $('#assess-new');
  if (anew) anew.onclick = () => {
    state.assessResult = null;
    state.assessFrom = null;
    state.assessDraft = null;
    state.assessMode = 'import';
    go('assess');
  };
  const toHistory = $('#assess-to-history');
  if (toHistory) toHistory.onclick = () => go('history');
  const change = $('#assess-change');
  if (change) change.onclick = () => {
    if (state.assessResult) state.assessResult.decisionRecorded = null;
    render();
  };

  document.querySelectorAll('[data-assess-mode]').forEach((b) => {
    b.onclick = () => {
      const next = b.dataset.assessMode;
      state.assessMode = next;
      if (next === 'import') state.assessDraft = null;
      render();
    };
  });
  document.querySelectorAll('[data-import]').forEach((b) => {
    b.onclick = async () => {
      const id = b.dataset.import;
      b.disabled = true;
      try {
        const row = await api('/api/applications/' + encodeURIComponent(id));
        const packet = Object.assign({}, row.packet || {}, {
          application_id: row.id,
          _meta: row,
        });
        state.assessDraft = packet;
        state.assessMode = 'manual';
        render();
      } catch (e) {
        b.disabled = false;
        toast('Could not import packet: ' + e.message);
      }
    };
  });
  fillAssessForm(state.assessDraft);

  document.querySelectorAll('[data-assess-act]').forEach((b) => {
    b.onclick = async () => {
      const rationale = ($('#assess-rationale') || {}).value || '';
      if (!rationale.trim()) {
        showAssessError('A rationale is required — it is what memory learns from.');
        return;
      }
      const id = state.assessResult && (state.assessResult.merchant_id
        || (state.assessResult.merchant && state.assessResult.merchant.id));
      if (!id) { showAssessError('Missing merchant id — run the assessment again.'); return; }
      document.querySelectorAll('[data-assess-act]').forEach((x) => { x.disabled = true; });
      try {
        const r = await post('/api/decide', {
          merchant_id: id, action: b.dataset.assessAct, rationale,
        });
        if (r.error) throw new Error(r.error);
        state.assessResult.decisionRecorded = {
          action: b.dataset.assessAct,
          rationale,
          reconciliation: (r.reconciliation && r.reconciliation.action) || 'recorded',
        };
        state.assessResult.merchant.status =
          { approve: 'approved', conditions: 'approved', decline: 'declined', escalate: 'pending' }[b.dataset.assessAct]
          || 'pending';
        state.portfolio = await api('/api/portfolio');
        const who = (state.assessResult.merchant && state.assessResult.merchant.name) || 'merchant';
        toast(`${REC_LABEL[b.dataset.assessAct] || b.dataset.assessAct} recorded for ${who}.`);
        go('history');
      } catch (e) {
        document.querySelectorAll('[data-assess-act]').forEach((x) => { x.disabled = false; });
        showAssessError('Could not record the decision: ' + e.message);
      }
    };
  });

  const form = $('#assess-form');
  if (!form) return;
  form.onsubmit = async (e) => {
    e.preventDefault();
    const val = (id) => String(($(id) || {}).value || '').trim();
    const name = val('#aname');
    if (!name) { showAssessError('Merchant name is required.'); return; }
    const purpose = val('#apur');
    const category = val('#acat');
    const country = val('#actry');
    const applicationId = (state.assessDraft && state.assessDraft.application_id) || '';
    if (!purpose && !applicationId) {
      showAssessError('A product description is required for a new merchant.');
      return;
    }
    if (!country && !applicationId) {
      showAssessError('Country is required.');
      return;
    }
    const payload = {
      name, category, signup_category: category, country,
      purpose,
      website: val('#aurl'),
      full_name: val('#afull'),
      entity_type: val('#aentity'),
      referral: val('#aref'),
      product_name: val('#aprod'),
      tax_category: val('#atax'),
      pricing_type: val('#aptype'),
      price: val('#aprice') ? Number(val('#aprice')) : 0,
      entitlements: [...document.querySelectorAll('input[name="ent"]:checked')].map((el) => el.value),
      application_id: applicationId || undefined,
      explain: true,
      web: true,
    };
    const run = $('#arun');
    if (run) { run.disabled = true; run.innerHTML = '<span class="spinner"></span>Assessing…'; }
    const err = $('#aerr'); if (err) err.hidden = true;
    const card = form.closest('.card') || form;
    let step = 0;
    card.innerHTML = `<div class="assess-wait">
      <div class="empty"><span class="spinner"></span>Assessing merchant…</div>
      <ul class="steps">${ASSESS_STEPS.map((s, i) =>
        `<li class="${i === 0 ? 'on' : ''}">${esc(s)}</li>`).join('')}</ul>
      <p class="tiny muted" style="text-align:center">One request — profile, memory, signals, then the brief.</p>
    </div>`;
    const timer = setInterval(() => {
      step = (step + 1) % ASSESS_STEPS.length;
      card.querySelectorAll('.steps li').forEach((li, i) => li.classList.toggle('on', i === step));
    }, 450);
    try {
      const r = await post('/api/assess', payload);
      clearInterval(timer);
      if (r.error) throw new Error(r.error);
      if (!r.decision || !r.merchant) throw new Error('Malformed assessment response.');
      state.assessResult = r;
      state.portfolio = await api('/api/portfolio');
      renderNav(); render();
    } catch (ex) {
      clearInterval(timer);
      toast('Assessment failed.');
      state.assessResult = null;
      render();
      setTimeout(() => showAssessError(
        ex.message === 'Failed to fetch'
          ? 'Server unavailable. Is the demo running?'
          : String(ex.message || ex)
      ), 0);
    }
  };
}

function statusAction(status) {
  return { declined: 'decline', approved: 'approve', terminated: 'decline' }[status] || null;
}

function hydrateAssessRow(row) {
  const src = row.brief || {};
  const brief = Object.assign({}, src);
  if (src.merchant) brief.merchant = Object.assign({}, src.merchant);
  const m = brief.merchant || {};
  const action = row.decision_action
    || (src.decisionRecorded && src.decisionRecorded.action)
    || (m.decided_by === 'analyst.you' ? statusAction(m.status) : null);
  const rationale = row.decision_rationale
    || (src.decisionRecorded && src.decisionRecorded.rationale)
    || m.rationale
    || '';
  if (action) {
    brief.decisionRecorded = {
      action,
      rationale,
      reconciliation: (src.decisionRecorded && src.decisionRecorded.reconciliation) || 'on file',
    };
  }
  return brief;
}

async function openAssessment(row) {
  if (!row) { toast('Assessment no longer in this session.'); return; }
  let packed = {
    decision_action: row.decision_action,
    decision_rationale: row.decision_rationale,
    brief: row.brief || row,
  };
  const mid = row.merchant_id
    || packed.brief.merchant_id
    || (packed.brief.merchant && packed.brief.merchant.id);
  if (mid) {
    try {
      const live = await api('/api/brief/' + encodeURIComponent(mid));
      if (live && live.merchant) {
        packed.brief = Object.assign({}, packed.brief, { merchant: live.merchant });
        if (!packed.decision_action && live.merchant.decided_by === 'analyst.you') {
          packed.decision_action = statusAction(live.merchant.status);
          packed.decision_rationale = packed.decision_rationale || live.merchant.rationale;
        }
      }
    } catch { /* snapshot is enough */ }
  }
  state.assessFrom = state.view === 'cases' ? 'cases' : 'history';
  state.assessResult = hydrateAssessRow(packed);
  go('assess');
}

let dirTimer;
function wire() {
  document.querySelectorAll('[data-open-assess]').forEach((tr) => {
    tr.onclick = () => openAssessment((state.assessmentIndex || {})[tr.dataset.openAssess]);
  });
  document.querySelectorAll('tr.click[data-id], .rowitem[data-id]').forEach((el) =>
    el.onclick = () => { state.briefId = el.dataset.id; render(); });
  document.querySelectorAll('[data-view]').forEach((el) => {
    if (el.closest('#nav')) return;
    el.onclick = (e) => { e.preventDefault(); go(el.dataset.view); };
  });
  document.querySelectorAll('[data-graph]').forEach((el) =>
    el.onclick = () => { state.graphId = el.dataset.graph; render(); });
  document.querySelectorAll('[data-page]').forEach((b) => b.onclick = () => {
    state.dir.page = +b.dataset.page; render();
  });

  const q = $('#dirq'), band = $('#dirband');
  if (q) {
    q.oninput = () => {
      clearTimeout(dirTimer);
      dirTimer = setTimeout(() => {
        state.dir.q = q.value; state.dir.page = 0; render();
        const f = $('#dirq'); if (f) { f.focus(); f.setSelectionRange(f.value.length, f.value.length); }
      }, 260);
    };
  }
  if (band) band.onchange = () => { state.dir.band = band.value; state.dir.page = 0; render(); };

  const nw = $('#newapp');
  if (nw) nw.onclick = () => {
    state.assessResult = null;
    state.assessFrom = null;
    state.assessDraft = null;
    state.assessMode = 'import';
    go('assess');
  };

  const back = $('#back');
  if (back) back.onclick = () => go(state.view);

  wireAssess();

  document.querySelectorAll('[data-act]').forEach((b) => b.onclick = async () => {
    const rationale = ($('#rationale') || {}).value || '';
    if (!rationale.trim()) { toast('A rationale is required — it is what memory learns from.'); return; }
    b.disabled = true;
    const r = await post('/api/decide', {
      merchant_id: state.briefId, action: b.dataset.act, rationale,
    });
    toast(`Recorded. Memory reconciled: ${r.reconciliation.action}.`);
    state.portfolio = await api('/api/portfolio');
    go('cases');
  });

  const run = $('#run');
  if (run) run.onclick = async () => {
    const id = $('#incident').value;
    run.disabled = true;
    run.innerHTML = '<span class="spinner"></span>Replaying…';
    try {
      const r = await post('/api/ingest', { merchant_id: id });
      toast(r.promoted
        ? `Promoted — catches ${r.caught_delta} more with no new false flags.`
        : 'Held back by the gate.');
      state.portfolio = await api('/api/portfolio');
      renderNav(); render();
    } catch (e) { toast('Replay failed: ' + e.message); run.disabled = false; }
  };
}

/* Global search routes to the directory -- the one surface that can answer it. */
let gsTimer;
$('#globalsearch').oninput = (e) => {
  clearTimeout(gsTimer);
  const v = e.target.value;
  gsTimer = setTimeout(() => {
    state.dir.q = v; state.dir.page = 0;
    if (state.view !== 'merchants' || state.briefId) go('merchants'); else render();
  }, 300);
};
$('#bell').onclick = () => go('cases');

$('#reset').onclick = async () => {
  await post('/api/reset');
  state.portfolio = await api('/api/portfolio');
  state.dir = { q: '', band: '', page: 0 };
  toast('Demo reset — portfolio rebuilt; assessment history kept.');
  go('homepage');
};

(async function boot() {
  state.portfolio = await api('/api/portfolio');
  renderNav();
  render();
})();
