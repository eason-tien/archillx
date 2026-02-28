const $ = (s) => document.querySelector(s);
const fmt = (o) => JSON.stringify(o, null, 2);
const esc = (s) => String(s ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll("""""", '&quot;');
let selectedProposalId = null;
function openPreviewWindow(url){ window.open(url, '_blank', 'noopener,noreferrer'); }

async function getJSON(url){ const r = await fetch(url); const data = await r.json(); if(!r.ok) throw new Error(fmt(data)); return data; }
async function postJSON(url, body){ const r = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})}); const data = await r.json(); if(!r.ok) throw new Error(fmt(data)); return data; }
function setCards(root, items){ root.innerHTML = items.map(i => `<div class="card"><div class="k">${i.label}</div><div class="v">${i.value}</div></div>`).join(''); }

function portalStatusMeta(status){
  const normalized = (status || 'unknown').toLowerCase();
  const map = {
    good: {label:'good', title:'Healthy / ready. This portal area currently looks OK.'},
    warn: {label:'warn', title:'Attention needed. There may be pending items or degraded signals.'},
    bad: {label:'bad', title:'Problem state. Review this area before proceeding.'},
    unknown: {label:'unknown', title:'No reliable state available yet.'}
  };
  return map[normalized] || map.unknown;
}

function renderOverviewPortalCards(context={}){
  const root = $('#overview-portal-cards');
  if(!root) return;
  const sections = context.sections || {};
  const restoreDrill = context.restoreDrill || {};
  const cards = [
    {title:'Release / rollback portal', desc:'Gate summary, latest evidence and HTML previews for release and rollback checks.', apiIds:['btn-open-gate-portal'], htmlIds:['btn-open-gate-portal-preview'], status: sections.release?.status || 'unknown', updated: sections.release?.last_updated || sections.rollback?.last_updated || '—'},
    {title:'Restore drill', desc:'Latest restore drill status and HTML preview for recovery readiness.', apiIds:['refresh-ops-shortcuts'], htmlIds:['btn-open-restore-preview'], status: sections.restore?.status || (restoreDrill.available ? 'good' : 'bad'), updated: sections.restore?.last_updated || restoreDrill.updated_at || '—'},
    {title:'Evolution portal', desc:'Portal index and HTML preview for the evolution subsystem.', apiIds:['btn-open-evolution-portal'], htmlIds:['btn-open-evolution-portal-preview'], status: sections.evolution?.status || 'unknown', updated: sections.evolution?.last_updated || '—'},
    {title:'Evolution final / nav', desc:'Final bundle, summary and navigation endpoints for evolution review.', apiIds:['btn-open-evolution-final','btn-open-evolution-summary','btn-open-evolution-nav'], htmlIds:['btn-open-evolution-final-preview'], status: sections.evolution?.status || 'unknown', updated: sections.evolution?.last_updated || '—'}
  ];
  root.innerHTML = cards.map((c) => {
    const badge = portalStatusMeta(c.status);
    const updatedTitle = c.updated && c.updated !== '—' ? `Last updated at ${c.updated}` : 'Last updated time not available';
    const apiCount = (c.apiIds || []).length;
    const htmlCount = (c.htmlIds || []).length;
    const apiButtons = (c.apiIds || []).map(id => `<button data-ref="${id}">${id.replace('btn-open-','').replace('refresh-','').replaceAll('-',' ')}</button>`).join('');
    const htmlButtons = (c.htmlIds || []).map(id => `<button data-ref="${id}" class="secondary">${id.includes('preview') ? 'open html' : id.replace('btn-open-','').replaceAll('-',' ')}</button>`).join('');
    return `<div class="portal-nav-card ${badge.label}" title="${badge.title}">
      <div class="portal-card-head"><h3>${c.title}</h3><span class="portal-status-badge ${badge.label}" title="${badge.title}">${badge.label}</span></div>
      <p>${c.desc}</p>
      <div class="portal-card-meta"><span class="meta-label" title="${updatedTitle}">Last updated</span><span class="meta-value" title="${updatedTitle}">${c.updated || '—'}</span></div>
      <div class="portal-action-groups">
        <div class="portal-action-group"><div class="group-head"><span class="group-label">API</span><span class="group-count" title="${apiCount} API shortcuts in this card">${apiCount}</span></div><div class="actions grouped">${apiButtons}</div></div>
        <div class="portal-action-group"><div class="group-head"><span class="group-label">HTML</span><span class="group-count" title="${htmlCount} HTML preview shortcuts in this card">${htmlCount}</span></div><div class="actions grouped">${htmlButtons}</div></div>
      </div>
    </div>`;
  }).join('');
  root.querySelectorAll('button[data-ref]').forEach(btn=>{ btn.onclick = () => { const ref = document.getElementById(btn.dataset.ref); if(ref) ref.click(); }; });
}


function timelineStatusMeta(status){
  const normalized = (status || 'unknown').toLowerCase();
  const map = {
    good: {label:'good', title:'Healthy / ready signal.'},
    warn: {label:'warn', title:'Attention needed. Review this item.'},
    bad: {label:'bad', title:'Problem state. Investigate before proceeding.'},
    unknown: {label:'unknown', title:'No reliable state available.'}
  };
  return map[normalized] || map.unknown;
}

function wireTimelineControls(){
  const statusSel = $('#timeline-filter-status');
  const areaSel = $('#timeline-filter-area');
  const windowSel = $('#timeline-filter-window');
  const expandBtn = $('#timeline-expand-all');
  const collapseBtn = $('#timeline-collapse-all');
  if(statusSel && !statusSel.dataset.wired){ statusSel.dataset.wired='1'; statusSel.onchange = () => renderOverviewEvidenceTimeline(window.__overviewContext || {}); }
  if(areaSel && !areaSel.dataset.wired){ areaSel.dataset.wired='1'; areaSel.onchange = () => renderOverviewEvidenceTimeline(window.__overviewContext || {}); }
  if(windowSel && !windowSel.dataset.wired){ windowSel.dataset.wired='1'; windowSel.onchange = () => renderOverviewEvidenceTimeline(window.__overviewContext || {}); }
  if(expandBtn && !expandBtn.dataset.wired){ expandBtn.dataset.wired='1'; expandBtn.onclick = () => { document.querySelectorAll('.timeline-group').forEach(g => g.classList.remove('collapsed')); }; }
  if(collapseBtn && !collapseBtn.dataset.wired){ collapseBtn.dataset.wired='1'; collapseBtn.onclick = () => { document.querySelectorAll('.timeline-group').forEach(g => g.classList.add('collapsed')); }; }
}


function withinTimelineWindow(ts, windowKey){
  if(!ts || windowKey === 'all') return true;
  const when = new Date(ts);
  if(Number.isNaN(when.getTime())) return true;
  const now = Date.now();
  const diff = now - when.getTime();
  const max = windowKey === '24h' ? 24*60*60*1000 : windowKey === '7d' ? 7*24*60*60*1000 : null;
  return max == null ? true : diff <= max;
}

function renderTimelineSummaryCards(items, windowKey){
  const root = $('#overview-timeline-summary');
  if(!root) return;
  const statuses = ['good','warn','bad','unknown'];
  const areas = ['release','rollback','restore','evolution'];
  const statusCounts = Object.fromEntries(statuses.map(s => [s, 0]));
  const areaCounts = Object.fromEntries(areas.map(a => [a, 0]));
  for(const item of items){
    const s = (item.status || 'unknown').toLowerCase();
    statusCounts[s] = (statusCounts[s] || 0) + 1;
    areaCounts[item.area] = (areaCounts[item.area] || 0) + 1;
  }
  const cards = [
    {label:'Window', value:windowKey, hint:'Active timeline window'},
    {label:'Entries', value:String(items.length), hint:'Visible timeline entries'},
    {label:'Bad', value:String(statusCounts.bad || 0), hint:'Items in problem state'},
    {label:'Warn', value:String(statusCounts.warn || 0), hint:'Items needing attention'},
    {label:'Release', value:String(areaCounts.release || 0), hint:'Release evidence entries'},
    {label:'Evolution', value:String(areaCounts.evolution || 0), hint:'Evolution evidence entries'}
  ];
  root.innerHTML = cards.map(c => `<div class="timeline-summary-card"><div class="k">${c.label}</div><div class="v">${c.value}</div><div class="hint">${c.hint}</div></div>`).join('');
}
function renderOverviewEvidenceTimeline(context={}){
  window.__overviewContext = context;
  wireTimelineControls();
  const root = $('#overview-evidence-timeline');
  if(!root) return;
  const sections = context.sections || {};
  const items = [
    ...(sections.release?.timeline || []).map(x => ({area:'release', ...x})),
    ...(sections.rollback?.timeline || []).map(x => ({area:'rollback', ...x})),
    ...(sections.restore?.timeline || []).map(x => ({area:'restore', ...x})),
    ...(sections.evolution?.timeline || []).map(x => ({area:'evolution', ...x}))
  ];
  const statusFilter = ($('#timeline-filter-status')?.value || 'all').toLowerCase();
  const areaFilter = ($('#timeline-filter-area')?.value || 'all').toLowerCase();
  const windowKey = ($('#timeline-filter-window')?.value || 'all').toLowerCase();
  const filtered = items.filter(item => {
    const s = (item.status || 'unknown').toLowerCase();
    const ts = item.updated_at || item.last_updated;
    return (statusFilter === 'all' || s === statusFilter) && (areaFilter === 'all' || item.area === areaFilter) && withinTimelineWindow(ts, windowKey);
  });
  renderTimelineSummaryCards(filtered, windowKey);
  if(!filtered.length){ root.innerHTML = '<div class="muted">No timeline entries match the current filters.</div>'; return; }
  const grouped = {};
  filtered.forEach(item => (grouped[item.area] ||= []).push(item));
  root.innerHTML = '<div class="timeline-groups">' + Object.entries(grouped).map(([area, group]) => {
    const areaStatus = group.some(i => (i.status||'').toLowerCase() === 'bad') ? 'bad' : group.some(i => (i.status||'').toLowerCase() === 'warn') ? 'warn' : group.every(i => (i.status||'').toLowerCase() === 'good') ? 'good' : 'unknown';
    const meta = timelineStatusMeta(areaStatus);
    const lastUpdated = group.map(i => i.updated_at || i.last_updated || '').filter(Boolean).sort().slice(-1)[0] || '—';
    return `<div class="timeline-group" data-area="${area}"><button class="timeline-group-toggle" title="Collapse or expand ${area} timeline entries"><span class="timeline-group-label">${area}</span><span class="timeline-group-badge ${meta.label}" title="${meta.title}">${meta.label}</span><span class="timeline-group-count" title="${group.length} entries in ${area}">${group.length}</span><span class="timeline-group-updated" title="Last updated ${lastUpdated}">${lastUpdated}</span></button><ul class="timeline-list">` + group.map(item => {
      const m = timelineStatusMeta(item.status);
      const updated = item.updated_at || item.last_updated || '—';
      return `<li class="${m.label}"><span class="timeline-area">${item.area}</span><span class="timeline-status ${m.label}" title="${m.title}">${m.label}</span><span class="timeline-label">${item.label}</span><span class="timeline-value" title="${String(item.value)}">${String(item.value)}</span><span class="timeline-updated" title="Last updated ${updated}">${updated}</span></li>`;
    }).join('') + '</ul></div>';
  }).join('') + '</div>';
  root.querySelectorAll('.timeline-group-toggle').forEach(btn => { btn.onclick = () => btn.parentElement.classList.toggle('collapsed'); });
}


function wireTabs(){ document.querySelectorAll('.tabs button').forEach(btn=>btn.onclick=()=>{ document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('active')); document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active')); btn.classList.add('active'); $('#tab-'+btn.dataset.tab).classList.add('active'); }); }
function selectedActor(){ return $('#proposal-actor').value || 'operator-ui'; }
function selectedReason(){ return $('#proposal-reason').value || null; }
function setSelectedProposalId(id){ selectedProposalId = id; $('#selected-proposal-id').textContent = id || '—'; }
function clearSelectionStyles(){ document.querySelectorAll('#proposal-table tr').forEach(tr=>tr.classList.remove('selected')); }

async function loadOverview(){
  const [health, ready, telemetry, gates, migration, restore, gatePortal, overviewStatus] = await Promise.all([
    getJSON('/v1/health'),
    getJSON('/v1/ready'),
    getJSON('/v1/telemetry'),
    getJSON('/v1/gates/summary'),
    getJSON('/v1/migration/state'),
    fetch('/v1/restore-drill/latest').then(async r => ({ok:r.ok, data: await r.json()})),
    getJSON('/v1/gates/portal/latest'),
    getJSON('/v1/system/overview-status')
  ]);
  const gateSummary = gates.summary || {};
  const sections = overviewStatus.sections || {};
  setCards($('#overview-cards'), [
    {label:'System', value: health.system || 'ArcHillx'},
    {label:'Ready', value: ready.status},
    {label:'Providers', value: (health.ai_providers||[]).length},
    {label:'HTTP req', value: telemetry.aggregate?.http?.requests_total ?? 0},
    {label:'Release pass', value: `${gateSummary.release?.passed ?? 0}/${gateSummary.release?.total ?? 0}`},
    {label:'Rollback pass', value: `${gateSummary.rollback?.passed ?? 0}/${gateSummary.rollback?.total ?? 0}`},
    {label:'Migration', value: migration.status || 'unknown'},
    {label:'Restore drill', value: restore.ok ? 'available' : 'missing'}
  ]);
  const statusCards = [
    {label:'Release', value:`${sections.release?.passed ?? 0}/${sections.release?.total ?? 0}`, status: sections.release?.status || 'unknown'},
    {label:'Rollback', value:`${sections.rollback?.passed ?? 0}/${sections.rollback?.total ?? 0}`, status: sections.rollback?.status || 'unknown'},
    {label:'Restore', value: sections.restore?.available ? 'available' : 'missing', status: sections.restore?.status || 'unknown'},
    {label:'Migration', value: sections.migration?.status || 'unknown', status: sections.migration?.ok ? 'good' : 'warn'},
    {label:'Evolution pending', value: sections.evolution?.pending_approval ?? 0, status: sections.evolution?.status || 'unknown'},
    {label:'Evolution actionable', value: sections.evolution?.actionable ?? 0, status: (sections.evolution?.actionable ?? 0) > 0 ? 'warn' : 'good'},
  ];
  const cardsRoot = $('#system-status-cards');
  cardsRoot.innerHTML = statusCards.map(i => `<div class="card status-card ${i.status || 'unknown'}"><div class="k">${i.label}</div><div class="v">${i.value}</div><div class="badge">${i.status || 'unknown'}</div></div>`).join('');
  $('#system-status-json').textContent = fmt(overviewStatus);
  $('#ready-json').textContent = fmt(ready);
  $('#telemetry-json').textContent = fmt(telemetry.aggregate || telemetry);
  $('#gates-summary').textContent = fmt(gates);
  $('#gates-latest').textContent = fmt(gateSummary.latest_paths || []);
  $('#ops-shortcuts').textContent = fmt({migration, restore_drill: restore.data});
  $('#portal-shortcuts').textContent = fmt({
    gate_portal: gatePortal.portal,
    gate_portal_preview: '/v1/gates/portal/preview',
    restore_drill_preview: '/v1/restore-drill/preview',
    evolution_portal: '/v1/evolution/portal',
    evolution_final: '/v1/evolution/final',
    evolution_summary: '/v1/evolution/summary',
    evolution_nav: '/v1/evolution/nav',
    system_portal_renderer: 'python scripts/render_system_delivery_index.py'
  });
  renderOverviewPortalCards({sections, restoreDrill: restore.data});
  renderOverviewEvidenceTimeline({sections});
}



let monitorTimer = null;

async function loadMonitor(){
  const data = await getJSON('/v1/system/monitor');
  const hbAge = data.recovery?.heartbeat_age_s;
  const hbAgeText = (typeof hbAge === 'number') ? `${hbAge.toFixed(1)}s` : 'n/a';
  setCards($('#monitor-cards'), [
    {label:'System', value:data.system || 'ArcHillx'},
    {label:'Version', value:data.version || 'unknown'},
    {label:'Ready', value:data.ready?.status || 'unknown'},
    {label:'DB', value:data.ready?.checks?.db ? 'ok' : 'fail'},
    {label:'Skills', value:data.ready?.checks?.skills ? 'ok' : 'fail'},
    {label:'Recovery mode', value:data.recovery?.mode || 'single'},
    {label:'Lock backend', value:data.recovery?.lock_backend || 'file'},
    {label:'Heartbeat age', value:hbAgeText},
    {label:'Entropy score', value:(data.entropy?.entropy_score ?? 'n/a')},
    {label:'Entropy risk', value:(data.entropy?.risk_level ?? 'unknown')},
  ]);
  $('#monitor-json').textContent = fmt(data);
  $('#monitor-recovery-json').textContent = fmt(data.recovery || {});
  $('#monitor-host-json').textContent = fmt(data.host || {});
  $('#monitor-telemetry-json').textContent = fmt(data.telemetry?.aggregate || data.telemetry || {});
  $('#monitor-entropy-json').textContent = fmt(data.entropy || {});
}

function setMonitorAutoRefresh(){
  if(monitorTimer){ clearInterval(monitorTimer); monitorTimer = null; }
  const sec = parseInt($('#monitor-refresh-interval')?.value || '0', 10);
  if(sec > 0){
    monitorTimer = setInterval(() => { loadMonitor().catch(e=>$('#monitor-json').textContent=e.message); }, sec * 1000);
  }
}

async function loadEvolution(){ const [status, summary] = await Promise.all([getJSON('/v1/evolution/status'), getJSON('/v1/evolution/summary')]); setCards($('#evolution-cards'), [{label:'Inspections', value: summary.counts?.inspections ?? 0},{label:'Proposals', value: summary.counts?.proposals ?? 0},{label:'Pending approval', value: summary.pipeline?.pending_approval ?? 0},{label:'Guard pass rate', value: summary.pipeline?.guard_pass_rate ?? 0}]); $('#evolution-summary').textContent = fmt(summary); $('#evolution-latest').textContent = fmt(status); }

async function loadEvolutionExtras(){
  const [portal, nav, finalData, summary] = await Promise.all([
    getJSON('/v1/evolution/portal'),
    getJSON('/v1/evolution/nav'),
    getJSON('/v1/evolution/final'),
    getJSON('/v1/evolution/summary')
  ]);
  $('#evolution-links').textContent = fmt({
    portal: portal.routes || portal.primary_routes || portal,
    nav: nav.primary_routes || nav,
    docs: portal.docs || nav.docs || []
  });
  $('#evolution-bundles').textContent = fmt({
    final: finalData.routes || finalData,
    pipeline: summary.pipeline || {},
    latest: summary.latest || {}
  });
}

async function renderEvolutionBundle(kind){
  const mapping = {
    dashboard: '/v1/evolution/dashboard/render',
    portal: '/v1/evolution/portal/render',
    final: '/v1/evolution/final/render'
  };
  const data = await postJSON(mapping[kind], {limit: 50});
  $('#evolution-bundles').textContent = fmt(data);
}



function artifactKeyPreview(manifest, key){
  const generated = manifest?.generated_at ? `Generated at ${manifest.generated_at}` : 'Generated time unavailable';
  const path = manifest?.paths?.[key] || 'No path available';
  const keyHelp = {
    patch: 'Unified diff patch artifact.',
    pr_title: 'Suggested PR title.',
    pr_draft: 'Suggested PR draft body.',
    commit_message: 'Suggested commit message.',
    tests: 'Suggested tests to add.',
    rollout: 'Suggested rollout notes.',
    risk: 'Risk assessment JSON.',
    manifest: 'Artifact manifest file.'
  };
  const body = [
    `Artifact key: ${key}`,
    '----------------',
    keyHelp[key] || 'Artifact file generated for this proposal.',
    '',
    `Path: ${path}`,
    generated
  ].join('\n');
  if(['pr_title','pr_draft','commit_message'].includes(key)){
    $('#proposal-pr-preview').textContent = body;
  } else {
    $('#proposal-patch-preview').textContent = body;
  }
}

async function loadArtifactPreview(id){ const data = await getJSON(`/v1/evolution/proposals/${id}/artifacts/preview`); const p = data.preview || {}; $('#proposal-pr-preview').textContent = ['PR TITLE','--------', p.pr_title || '', '', 'PR DRAFT','--------', p.pr_draft || '', '', 'COMMIT MESSAGE','--------', p.commit_message || ''].join('\n'); $('#proposal-patch-preview').textContent = ['PATCH','-----', p.patch || '', '', 'TESTS TO ADD','------------', p.tests || '', '', 'ROLLOUT NOTES','-------------', p.rollout || ''].join('\n'); }

function renderArtifactManifestBadges(manifest){
  const root = $('#proposal-artifact-badges');
  if(!root) return;
  const groupForKey = (key) => {
    if(['pr_title','pr_draft','commit_message'].includes(key)) return 'PR';
    if(['patch','manifest'].includes(key)) return 'Patch';
    if(['tests','rollout'].includes(key)) return 'Ops';
    if(['risk'].includes(key)) return 'Risk';
    return 'Other';
  };
  if(!manifest || !manifest.artifact_count){
    root.innerHTML = [
      '<div class="artifact-group"><div class="artifact-group-head"><span class="group-label">Manifest</span><span class="group-count" title="0 artifact groups loaded">0</span></div><div class="artifact-group-body"><span class="artifact-badge status-missing" title="Artifacts have not been rendered for this proposal yet. Render artifacts to generate the manifest bundle.">No artifacts</span><span class="artifact-badge state status-neutral" title="No manifest data is currently loaded for this proposal.">Manifest: missing</span></div></div>'
    ].join('');
    return;
  }
  const keys = manifest.artifact_keys || [];
  const grouped = {};
  keys.forEach(k => { (grouped[groupForKey(k)] ||= []).push(k); });
  const generated = !!manifest.generated_at;
  const hasCore = ['patch', 'pr_title', 'pr_draft', 'commit_message'].every(k => keys.includes(k));
  const richness = manifest.artifact_count >= 6 ? 'rich' : (manifest.artifact_count >= 3 ? 'minimal' : 'thin');
  const healthClass = hasCore ? (manifest.artifact_count >= 6 ? 'status-good' : 'status-warn') : 'status-bad';
  const healthText = hasCore ? (manifest.artifact_count >= 6 ? 'Manifest: complete' : 'Manifest: partial') : 'Manifest: incomplete';
  const countHelp = `Manifest contains ${manifest.artifact_count} artifact file(s).`;
  const generatedHelp = generated ? `Artifacts were rendered at ${manifest.generated_at}.` : 'Artifacts exist but generated_at is missing from the manifest.';
  const healthHelp = hasCore
    ? (manifest.artifact_count >= 6
        ? 'Core patch, PR and commit artifacts are present with supporting files.'
        : 'Core patch artifacts exist, but the bundle is still partial and may be missing supporting files.')
    : 'Core patch artifacts are missing. Reviewer should render artifacts again before approval.';
  const bundleHelp = richness === 'rich'
    ? 'Rich bundle: patch, PR, commit, rollout and related artifact files are all present.'
    : richness === 'minimal'
      ? 'Minimal bundle: enough artifacts exist for review, but supporting files are limited.'
      : 'Thin bundle: very small artifact set; reviewer should verify whether rendering completed.';
  const summary = [
    `<div class="artifact-group"><div class="artifact-group-head"><span class="group-label">Summary</span><span class="group-count" title="Summary badges for this manifest">4</span></div><div class="artifact-group-body">` +
      `<span class="artifact-badge count ${healthClass}" title="${esc(countHelp)}">Artifacts: ${manifest.artifact_count}</span>` +
      `<span class="artifact-badge state ${generated ? 'status-good' : 'status-neutral'}" title="${esc(generatedHelp)}">Generated: ${generated ? 'yes' : 'unknown'}</span>` +
      `<span class="artifact-badge state ${healthClass}" title="${esc(healthHelp)}">${healthText}</span>` +
      `<span class="artifact-badge state ${richness === 'rich' ? 'status-good' : (richness === 'minimal' ? 'status-warn' : 'status-bad')}" title="${esc(bundleHelp)}">Bundle: ${richness}</span>` +
    `</div></div>`
  ];
  const order = ['PR','Patch','Ops','Risk','Other'];
  for(const group of order){
    const gkeys = grouped[group] || [];
    if(!gkeys.length) continue;
    const badges = gkeys.slice(0, 4).map(k => `<button type="button" class="artifact-badge key-badge clickable" data-artifact-key="${esc(k)}" title="Artifact key: ${esc(k)} — click to preview summary">${esc(k)}</button>`).join('');
    const extra = gkeys.length > 4 ? `<span class="artifact-badge state status-neutral" title="There are ${gkeys.length - 4} additional ${group} entries not shown in the preview badges.">+${gkeys.length - 4} more</span>` : '';
    summary.push(`<div class="artifact-group"><div class="artifact-group-head"><span class="group-label">${group}</span><span class="group-count" title="${gkeys.length} ${group} artifact entries">${gkeys.length}</span></div><div class="artifact-group-body">${badges}${extra}</div></div>`);
  }
  root.innerHTML = summary.join('');
  root.querySelectorAll('[data-artifact-key]').forEach(btn => {
    btn.onclick = () => artifactKeyPreview(manifest, btn.dataset.artifactKey);
  });
}

async function loadArtifactManifest(id){ const data = await getJSON(`/v1/evolution/proposals/${id}/artifacts/manifest`); const m = data.manifest || {}; renderArtifactManifestBadges(m); $('#proposal-artifact-manifest').textContent = fmt(m); }

function renderIntegratedReview(nav, detail){
  const proposal = detail || nav?.proposal || {};
  const risk = proposal.risk || {};
  const summary = {
    proposal_id: proposal.proposal_id,
    title: proposal.title,
    status: proposal.status,
    subject: proposal.source_subject,
    risk_level: risk.risk_level || null,
    risk_score: risk.risk_score ?? null,
    approval_required: proposal.approval_required ?? null,
    auto_apply_allowed: risk.auto_apply_allowed ?? null
  };
  const guard = nav?.guard || null;
  const baseline = nav?.baseline || null;
  $('#proposal-review-summary').textContent = fmt(summary);
  $('#proposal-guard-summary').textContent = fmt(guard ? {guard_id: guard.guard_id, status: guard.status, checks: (guard.checks || []).map(c => ({name:c.name, status:c.status}))} : {guard: 'not available'});
  $('#proposal-baseline-summary').textContent = fmt(baseline ? {baseline_id: baseline.baseline_id, regression_detected: baseline.regression_detected, summary: baseline.summary, diff: baseline.diff} : {baseline: 'not available'});
}


async function loadProposalActions(){ const actions = await getJSON('/v1/evolution/actions/list?limit=20'); $('#proposal-actions').textContent = fmt(actions); }

async function loadProposalDetail(id){ const [detail, nav] = await Promise.all([getJSON('/v1/evolution/proposals/' + id), getJSON(`/v1/evolution/evidence/nav/proposals/${id}`)]); $('#proposal-detail').textContent = fmt(detail); renderIntegratedReview(nav, detail); $('#proposal-actions').textContent = fmt({proposal_actions: nav.actions || []}); if(detail.artifact_paths && Object.keys(detail.artifact_paths).length){ $('#proposal-artifacts').textContent = fmt(detail.artifact_paths); await loadArtifactPreview(id); await loadArtifactManifest(id); } else { $('#proposal-artifacts').textContent = 'No artifacts rendered yet'; renderArtifactManifestBadges(null); $('#proposal-artifact-manifest').textContent = 'Select a proposal to view artifact manifest'; $('#proposal-pr-preview').textContent = 'Select a proposal to preview PR title / PR draft / commit message'; $('#proposal-patch-preview').textContent = 'Select a proposal to preview patch / tests / rollout notes'; } }

async function loadProposals(){ const qs = new URLSearchParams(); if($('#proposal-status').value) qs.set('status',$('#proposal-status').value); if($('#proposal-risk').value) qs.set('risk_level',$('#proposal-risk').value); if($('#proposal-subject').value) qs.set('subject',$('#proposal-subject').value); const data = await getJSON('/v1/evolution/proposals/list?'+qs.toString()); const tbody = $('#proposal-table'); tbody.innerHTML = ''; (data.items||[]).forEach(item=>{ const tr = document.createElement('tr'); tr.innerHTML = `<td>${item.proposal_id}</td><td>${item.status}</td><td>${item.risk?.risk_level||''}</td><td>${item.source_subject}</td><td>${item.title}</td>`; tr.onclick = async ()=>{ clearSelectionStyles(); tr.classList.add('selected'); setSelectedProposalId(item.proposal_id); await loadProposalDetail(item.proposal_id); }; tbody.appendChild(tr); }); if(!(data.items||[]).length) tbody.innerHTML='<tr><td colspan="5">No proposals</td></tr>'; await loadProposalActions(); }


function renderExportResult(data){
  const root = $('#proposal-export-result');
  if(!root) return;
  if(!data || typeof data !== 'object'){ root.textContent = 'No export result'; return; }
  const links = [
    ['json', data.json],
    ['markdown', data.markdown],
    ['html', data.html],
  ].filter(([, path]) => !!path);
  if(!links.length){ root.textContent = fmt(data); return; }
  root.innerHTML = links.map(([kind, path]) => `<div class="export-link-row"><span class="export-tag">${kind}</span><a href="/${String(path).replace(/^\/+/,'')}" target="_blank" rel="noopener noreferrer">${path}</a></div>`).join('');
}

async function exportReview(section){
  if(!selectedProposalId){ $('#proposal-export-result').textContent = 'Select a proposal first'; return; }
  const data = await postJSON(`/v1/evolution/proposals/${selectedProposalId}/review/export?section=${encodeURIComponent(section)}`, {});
  renderExportResult(data);
}

async function runProposalAction(kind){ if(!selectedProposalId){ $('#proposal-action-result').textContent = 'Select a proposal first'; return; } const payload = { actor: selectedActor(), reason: selectedReason() }; const data = await postJSON(`/v1/evolution/proposals/${selectedProposalId}/${kind}`, payload); $('#proposal-action-result').textContent = fmt(data); await loadProposalDetail(selectedProposalId); await loadProposalActions(); await loadEvolution().catch(()=>{}); }
async function renderArtifacts(){ if(!selectedProposalId){ $('#proposal-artifacts').textContent = 'Select a proposal first'; return; } const data = await postJSON(`/v1/evolution/proposals/${selectedProposalId}/artifacts/render`, {}); $('#proposal-artifacts').textContent = fmt(data); await loadProposalDetail(selectedProposalId); await loadArtifactPreview(selectedProposalId); }

async function loadEvidence(){ const [idx, portal] = await Promise.all([getJSON('/v1/evolution/evidence/index'), getJSON('/v1/evolution/portal')]); $('#evidence-index').textContent = fmt(idx); $('#portal-json').textContent = fmt(portal); }

window.addEventListener('DOMContentLoaded', ()=>{
  wireTabs();
  renderOverviewPortalCards();
  loadOverview().catch(e=>$('#ready-json').textContent=e.message);
  loadMonitor().catch(e=>$('#monitor-json').textContent=e.message);
  loadEvolution().catch(e=>$('#evolution-summary').textContent=e.message);
  loadEvolutionExtras().catch(e=>$('#evolution-links').textContent=e.message);
  loadProposals().catch(e=>$('#proposal-detail').textContent=e.message);
  loadEvidence().catch(e=>$('#evidence-index').textContent=e.message);
  $('#refresh-proposals').onclick=()=>loadProposals();
  $('#refresh-monitor').onclick=()=>loadMonitor().catch(e=>$('#monitor-json').textContent=e.message);
  $('#monitor-refresh-interval').onchange=()=>setMonitorAutoRefresh();
  setMonitorAutoRefresh();
  $('#refresh-gates').onclick=()=>loadOverview().catch(e=>$('#gates-summary').textContent=e.message);
  $('#refresh-ops-shortcuts').onclick=()=>loadOverview().catch(e=>$('#ops-shortcuts').textContent=e.message);
  $('#btn-open-gate-portal').onclick=()=>getJSON('/v1/gates/portal/latest').then(d=>$('#portal-shortcuts').textContent=fmt(d)).catch(e=>$('#portal-shortcuts').textContent=e.message);
  $('#btn-open-gate-portal-preview').onclick=()=>openPreviewWindow('/v1/gates/portal/preview');
  $('#btn-open-restore-preview').onclick=()=>openPreviewWindow('/v1/restore-drill/preview');
  $('#btn-open-evolution-portal').onclick=()=>getJSON('/v1/evolution/portal').then(d=>$('#portal-shortcuts').textContent=fmt(d)).catch(e=>$('#portal-shortcuts').textContent=e.message);
  $('#btn-open-evolution-portal-preview').onclick=()=>openPreviewWindow('/v1/evolution/portal/preview');
  $('#btn-open-evolution-final').onclick=()=>getJSON('/v1/evolution/final').then(d=>$('#portal-shortcuts').textContent=fmt(d)).catch(e=>$('#portal-shortcuts').textContent=e.message);
  $('#btn-open-evolution-final-preview').onclick=()=>openPreviewWindow('/v1/evolution/final/preview');
  $('#btn-open-evolution-summary').onclick=()=>getJSON('/v1/evolution/summary').then(d=>$('#portal-shortcuts').textContent=fmt(d)).catch(e=>$('#portal-shortcuts').textContent=e.message);
  $('#btn-open-evolution-nav').onclick=()=>getJSON('/v1/evolution/nav').then(d=>$('#portal-shortcuts').textContent=fmt(d)).catch(e=>$('#portal-shortcuts').textContent=e.message);
  $('#btn-open-system-portal').onclick=()=>fetch('/ui/static/index.html').then(()=>{ $('#portal-shortcuts').textContent = fmt({system_portal_hint: 'Run python scripts/render_system_delivery_index.py to generate system delivery portal bundle', outputs: ['evidence/dashboards/system_delivery_portal_*.json','evidence/dashboards/system_delivery_portal_*.md','evidence/dashboards/system_delivery_portal_*.html']}); }).catch(e=>$('#portal-shortcuts').textContent=e.message);
  $('#btn-open-portal').onclick=()=>getJSON('/v1/evolution/portal').then(d=>$('#evolution-links').textContent=fmt(d)).catch(e=>$('#evolution-links').textContent=e.message);
  $('#btn-open-nav').onclick=()=>getJSON('/v1/evolution/nav').then(d=>$('#evolution-links').textContent=fmt(d)).catch(e=>$('#evolution-links').textContent=e.message);
  $('#btn-open-final').onclick=()=>getJSON('/v1/evolution/final').then(d=>$('#evolution-bundles').textContent=fmt(d)).catch(e=>$('#evolution-bundles').textContent=e.message);
  $('#btn-render-dashboard').onclick=()=>renderEvolutionBundle('dashboard').catch(e=>$('#evolution-bundles').textContent=e.message);
  $('#btn-render-portal').onclick=()=>renderEvolutionBundle('portal').catch(e=>$('#evolution-bundles').textContent=e.message);
  $('#btn-render-final').onclick=()=>renderEvolutionBundle('final').catch(e=>$('#evolution-bundles').textContent=e.message);
  $('#btn-open-dashboard-summary').onclick=()=>getJSON('/v1/evolution/summary').then(d=>$('#evolution-bundles').textContent=fmt(d)).catch(e=>$('#evolution-bundles').textContent=e.message);
  $('#refresh-evidence').onclick=()=>loadEvidence();
  $('#btn-approve').onclick=()=>runProposalAction('approve').catch(e=>$('#proposal-action-result').textContent=e.message);
  $('#btn-reject').onclick=()=>runProposalAction('reject').catch(e=>$('#proposal-action-result').textContent=e.message);
  $('#btn-apply').onclick=()=>runProposalAction('apply').catch(e=>$('#proposal-action-result').textContent=e.message);
  $('#btn-rollback').onclick=()=>runProposalAction('rollback').catch(e=>$('#proposal-action-result').textContent=e.message);
  $('#btn-render-artifacts').onclick=()=>renderArtifacts().catch(e=>$('#proposal-artifacts').textContent=e.message);
  $('#btn-export-review-artifacts').onclick=()=>exportReview('artifacts').catch(e=>$('#proposal-export-result').textContent=e.message);
  $('#btn-export-review-baseline').onclick=()=>exportReview('baseline').catch(e=>$('#proposal-export-result').textContent=e.message);
  $('#btn-export-review-guard').onclick=()=>exportReview('guard').catch(e=>$('#proposal-export-result').textContent=e.message);
  $('#btn-export-review-all').onclick=()=>exportReview('all').catch(e=>$('#proposal-export-result').textContent=e.message);
});
