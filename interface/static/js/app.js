/**
 * DEEP AI Interface - Application
 * Three.js dense neon particle sphere with UnrealBloom post-processing.
 */

// ===== STATE =====
let state = "idle";
let currentStreamMessage = null;
let ws = null, wsConnected = false;

// ===== MATH HELPERS =====
function lerp(a, b, t) { return a + (b - a) * t; }

// ===== NEURAL GRAPH (live map of DEEP subsystems) =====
// Replaces the particle sphere as the centerpiece. Nodes glow when their
// subsystem fires events on the EventBus (polled from /debug/events); the
// core pulses with chat state + voice amplitude.
let ngCanvas, ngCtx, ngW = 0, ngH = 0;
let ngLastEventTs = null;
let ngCx = 0, ngCy = 0, ngCoreR = 26;     // live core geometry (for hit-testing)
let ngSel = null, ngHover = null;          // selected / hovered subsystem id
let ngDetailEl = null;
let ngRot = 0;                             // ring rotation (pauses while a node is open)

// DEEP palette — temple gold over indigo void. Gold = consciousness/attention,
// indigo = the unmanifest. Each chat state shifts the ambient accent.
const STATE_RGB = {            // accent per chat state (RGB 0-255)
  idle:       [232, 185, 116],  // temple gold
  listening:  [245, 225, 170],  // bright ivory-gold (receptive)
  processing: [230, 150,  70],  // saffron (active reasoning)
  speaking:   [235, 170, 130],  // rose-gold (expression)
};
let ngAccent = [232, 185, 116];

// Comprehensive map of DEEP's real architecture. Each node expands into its
// actual sub-components, and binds to a live API for real-time metrics.
const NG_NODES = [
  { id:'brain', label:'REASONING', color:[245,210,150], act:0,
    desc:'Multi-LLM reasoning core. Routes each request to the best provider and runs the agent + tool loop.',
    comps:['Multi-LLM Router','Agent Loop','Tool Registry','Intent Router'],
    api:'/api/status', metric:d => d.model ? ('active · ' + d.model) : '' },
  { id:'memory', label:'MEMORY', color:[150,140,230], act:0,
    desc:'Persistent vector memory and session recall via ChromaDB embeddings.',
    comps:['LTM Vector Store','ChromaDB','Session History','Pattern Memory'],
    api:'/api/knowledge/stats', metric:d => d.entities!=null ? (d.entities + ' entities stored') : '' },
  { id:'knowledge', label:'KNOWLEDGE', color:[205,200,135], act:0,
    desc:'Knowledge graph linking entities, concepts and research papers.',
    comps:['Knowledge Graph','Ingester','Concept Linker','Breakthrough Detector'],
    api:'/api/knowledge/stats', metric:d => d.relationships!=null ? (d.entities + ' nodes · ' + d.relationships + ' links') : '' },
  { id:'research', label:'RESEARCH', color:[180,160,230], act:0,
    desc:'Autonomous background research across RSS feeds and web search.',
    comps:['RSS Feeds','Web Search','Findings Store','Briefing Engine'],
    api:'/api/research/stats', metric:d => ((d.total_findings??0) + ' findings · ' + (d.topics??0) + ' topics') },
  { id:'predictive', label:'PREDICTIVE', color:[235,180,90], act:0,
    desc:'Learns your behavioural patterns and anticipates your next move.',
    comps:['Time Patterns','Sequence Patterns','Suggestion Engine'],
    api:'/api/predictive/stats', metric:d => ((d.total_interactions??0) + ' interactions learned') },
  { id:'agents', label:'AGENTS', color:[220,140,185], act:0,
    desc:'Spawns specialised sub-agents for complex multi-step tasks.',
    comps:['Researcher','Coder','Analyst','CyberSec','Swarm Bus'],
    api:'/api/agents/stats', metric:d => ((d.agents_running??0) + ' running · ' + (d.total_tasks_completed??0) + ' done') },
  { id:'security', label:'SECURITY', color:[230,110,85], act:0,
    desc:'Network defence — device discovery, threat and rogue-AP detection.',
    comps:['Net Scanner','Threat Monitor','Evil-Twin Detector','Pi-hole DNS','Proximity'],
    api:'/api/security/status', metric:d => { const s=d.summary||{}; return s.total!=null ? (s.total + ' devices · ' + (s.suspicious||0) + ' suspicious') : ''; } },
  { id:'voice', label:'VOICE', color:[240,200,160], act:0,
    desc:'Speech in and out — Whisper STT, neural TTS, and wake-word detection.',
    comps:['Whisper STT','Edge / Piper TTS','Wake Word','Bluetooth Audio','Spatial Audio'],
    api:null, metric:()=>'' },
];
const NG_LINKS = [['brain','memory'],['brain','knowledge'],['brain','voice'],
                  ['security','predictive'],['research','knowledge'],['memory','knowledge']];
let ngCore = { act:0 };

function ngNode(id){ return NG_NODES.find(n => n.id === id); }
function ngActivate(id, amt){ const n = id==='core' ? ngCore : ngNode(id); if (n) n.act = Math.min(1, (n.act||0) + (amt||0.9)); }

// ── Interaction: hit-testing, selection, expandable detail panel ──────────
function ngHitTest(mx, my){
  if (Math.hypot(mx - ngCx, my - ngCy) < ngCoreR + 8) return 'core';
  for (const n of NG_NODES){ if (n.x != null && Math.hypot(mx - n.x, my - n.y) < 22) return n.id; }
  return null;
}

function ngEnsureDetail(){
  if (ngDetailEl) return;
  const el = document.createElement('div');
  el.id = 'ng-detail';
  el.style.cssText = 'position:fixed;top:84px;left:24px;width:284px;max-width:42vw;z-index:16;'
    + 'padding:16px 18px;border-radius:14px;background:rgba(10,16,26,0.74);'
    + 'backdrop-filter:blur(18px) saturate(1.3);-webkit-backdrop-filter:blur(18px) saturate(1.3);'
    + 'border:1px solid rgba(232,185,116,0.22);'
    + 'box-shadow:0 12px 44px rgba(0,0,0,0.5),0 0 0 1px rgba(232,185,116,0.06),inset 0 0 30px rgba(232,185,116,0.04);'
    + 'opacity:0;transform:translateY(8px);transition:opacity .25s ease,transform .25s ease;pointer-events:none;color:#eaf6ff;';
  document.body.appendChild(el);
  ngDetailEl = el;
}

function ngUpdateDetail(){
  if (!ngSel || !ngDetailEl) return;
  const n = ngNode(ngSel); if (!n) return;
  const [r,g,b] = n.color;
  const comps = (n.comps||[]).map(c =>
    `<div style="display:flex;align-items:center;gap:8px;margin:5px 0;font:500 11px var(--font-mono,monospace);color:rgba(234,246,255,.72)">`
    + `<span style="width:5px;height:5px;border-radius:50%;background:rgb(${r},${g},${b});box-shadow:0 0 8px rgba(${r},${g},${b},.8)"></span>${c}</div>`).join('');
  ngDetailEl.innerHTML =
      `<div style="font:700 13px var(--font-display,monospace);letter-spacing:2px;color:rgb(${r},${g},${b});text-shadow:0 0 14px rgba(${r},${g},${b},.5)">${n.label}</div>`
    + `<div style="font:400 11px var(--font-mono,monospace);color:rgba(234,246,255,.55);margin:8px 0 12px;line-height:1.55">${n.desc||''}</div>`
    + (n.stat ? `<div style="font:600 11px var(--font-mono,monospace);color:rgb(${r},${g},${b});margin-bottom:12px">▸ ${n.stat}</div>` : '')
    + `<div style="font:600 9px var(--font-display,monospace);letter-spacing:.18em;text-transform:uppercase;color:rgba(234,246,255,.35);margin-bottom:8px;border-top:1px solid rgba(232,185,116,.12);padding-top:10px">Components</div>`
    + comps;
}

function ngSelect(id){
  ngEnsureDetail();
  ngSel = id;
  ngUpdateDetail();
  const n = ngNode(id);
  if (n && n.api){ fetch(n.api).then(r => r.ok && r.json()).then(d => { if (d){ n.stat = (n.metric ? n.metric(d) : '') || n.stat; ngUpdateDetail(); } }).catch(()=>{}); }
  requestAnimationFrame(() => { ngDetailEl.style.opacity = '1'; ngDetailEl.style.transform = 'translateY(0)'; });
}

function ngDeselect(){
  ngSel = null;
  if (ngDetailEl){ ngDetailEl.style.opacity = '0'; ngDetailEl.style.transform = 'translateY(8px)'; }
}

async function ngPollMetrics(){
  await Promise.all(NG_NODES.map(async n => {
    if (!n.api) return;
    try { const r = await fetch(n.api); if (!r.ok) return; const d = await r.json(); n.stat = (n.metric ? n.metric(d) : '') || n.stat || ''; } catch(e){}
  }));
  if (ngSel) ngUpdateDetail();
}

function ngEventToNode(name){
  name = (name||'').toLowerCase();
  if (/tts|stt|voice|wake|speech/.test(name)) return 'voice';
  if (/^network|_ap|device|threat|scan|evil_twin|proximity/.test(name)) return 'security';
  if (/predict/.test(name)) return 'predictive';
  if (/research/.test(name)) return 'research';
  if (/knowledge|concept|breakthrough|graph/.test(name)) return 'knowledge';
  if (/memory|ltm/.test(name)) return 'memory';
  if (/agent|swarm|skill/.test(name)) return 'agents';
  if (/deep_response|token|thinking|llm|brain|generation/.test(name)) return 'brain';
  return 'core';
}

// Events that are WiFi/network background noise — shown in topology panel, not activity feed
const NG_ACTIVITY_SUPPRESS = new Set([
  'persistent_unknown_ap', 'open_network_nearby', 'network_flow_recorded',
  'system_snapshot_collected', 'stt_listening', 'stt_processing',
]);
// Rate-limit: same human label shown at most once per 30 s to prevent bursts
const _activityRateMap = {};
const ACTIVITY_RATE_MS = 30_000;

async function ngPollEvents(){
  try {
    const r = await fetch('/debug/events'); if (!r.ok) return;
    const hist = (await r.json()).history || [];
    for (const ev of hist){
      if (ngLastEventTs && ev.timestamp <= ngLastEventTs) continue;
      ngActivate(ngEventToNode(ev.event), 0.85);
      ngCore.act = Math.min(1, ngCore.act + 0.2);
      if (ngLastEventTs) {
        // Skip background noise events (WiFi APs, raw network flows, etc.)
        if (NG_ACTIVITY_SUPPRESS.has(ev.event)) continue;

        // Skip low/info severity security alerts
        if (ev.event === 'security_alert') {
          const sev = ev.payload?.severity;
          if (sev === 'info' || sev === 'low') continue;
        }

        // Rate-limit: same label at most once per 30 s
        const label = ngHumanize(ev.event, ev.payload);
        const now = Date.now();
        if (_activityRateMap[label] && now - _activityRateMap[label] < ACTIVITY_RATE_MS) continue;
        _activityRateMap[label] = now;

        ngAddActivity(ev.event, ev.payload);
      }
    }
    if (hist.length) ngLastEventTs = hist[hist.length-1].timestamp;
  } catch(e){}
}

// ── Live activity feed + active-model badge ───────────────────────────────
const NG_EVENT_LABELS = {
  system_snapshot_collected: 'System snapshot',
  network_flow_recorded: 'Network flow analysed',
  persistent_unknown_ap: 'Unknown access point seen',
  predictive_event: 'Prediction updated',
  prediction_ready: 'New prediction ready',
  tts_complete: 'Finished speaking',
  tts_sentence_spoken: 'Speaking',
  deep_response: 'Response generated',
  thinking: 'Thinking',
};
function ngHumanize(ev, payload){
  // Security alerts: use the payload title for precision
  if (ev === 'security_alert' && payload?.title) return payload.title;
  if (NG_EVENT_LABELS[ev]) return NG_EVENT_LABELS[ev];
  return (ev || 'event').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
function ngAddActivity(ev, payload){
  const feed = document.getElementById('activityFeed');
  if (!feed) return;
  feed.querySelector('.activity-empty')?.remove();
  const label = ngHumanize(ev, payload);
  const now = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});

  // Collapse consecutive identical events into one "Label ×N" row so nothing floods the feed.
  const top = feed.firstElementChild;
  if (top && top.dataset.label === label){
    const c = (parseInt(top.dataset.count || '1', 10) + 1);
    top.dataset.count = c;
    const txt = top.querySelector('.activity-text'); if (txt) txt.textContent = `${label} ×${c}`;
    const tm = top.querySelector('.activity-time'); if (tm) tm.textContent = now;
    return;
  }

  const n = ngNode(ngEventToNode(ev));
  const [r,g,b] = (n && n.color) || ngAccent;
  const row = document.createElement('div');
  row.className = 'activity-row';
  row.dataset.label = label; row.dataset.count = '1';
  row.innerHTML = `<span class="activity-dot" style="background:rgb(${r},${g},${b});box-shadow:0 0 8px rgba(${r},${g},${b},.7)"></span>`
    + `<span class="activity-text">${label}</span>`
    + `<span class="activity-time">${now}</span>`;
  feed.prepend(row);
  while (feed.children.length > 18) feed.removeChild(feed.lastChild);
}

function prettyModel(m){
  m = (m || '').toLowerCase();
  if (m.includes('claude-opus-4-8') || m.includes('claude-opus-4.8')) return 'Claude Opus 4.8';
  if (m.includes('claude-opus-4'))   return 'Claude Opus 4';
  if (m.includes('claude-sonnet-4-6') || m.includes('claude-sonnet-4.6')) return 'Claude Sonnet 4.6';
  if (m.includes('claude-sonnet-4')) return 'Claude Sonnet 4';
  if (m.includes('claude-haiku-4'))  return 'Claude Haiku 4.5';
  if (m.includes('claude-3-5-sonnet')) return 'Claude 3.5 Sonnet';
  if (m.includes('claude-3-opus'))   return 'Claude 3 Opus';
  if (m.includes('claude'))          return 'Claude';
  if (m.includes('llama-3.3-70b') || m.includes('llama3.3')) return 'Llama 3.3 70B';
  if (m.includes('llama3.2') || m.includes('llama-3.2')) return 'Llama 3.2';
  if (m.includes('llama-3.1-8b'))    return 'Llama 3.1 8B';
  if (m.includes('mixtral'))         return 'Mixtral 8x7B';
  if (m.includes('gemini-2.0-flash') || m.includes('gemini-flash')) return 'Gemini 2.0 Flash';
  if (m.includes('gemini-pro'))      return 'Gemini Pro';
  if (m.includes('gemini'))          return 'Gemini';
  if (m.includes('gpt-4o'))          return 'GPT-4o';
  if (m.includes('gpt'))             return 'GPT';
  return m ? m.slice(0, 22) : 'DEEP';
}
function setActiveModel(m){ const el = document.getElementById('activeModel'); if (el) el.textContent = prettyModel(m); }

// Smooth bezier edge with a rotational bow + a signal pulse travelling the curve.
function ngDrawEdge(x1, y1, x2, y2, act, opts){
  opts = opts || {};
  const [r,g,b] = opts.color || ngAccent;
  const thin = opts.thin;
  const frac = (opts.frac != null) ? opts.frac : 0.16;   // curvature (perp offset / length)
  const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy) || 1;
  const cpx = (x1 + x2) / 2 - dy / len * len * frac;     // control point, bowed one way
  const cpy = (y1 + y2) / 2 + dx / len * len * frac;     //   → gives the pinwheel curve
  const baseA = (opts.baseA != null) ? opts.baseA : (thin ? 0.05 : 0.11);
  ngCtx.strokeStyle = `rgba(${r|0},${g|0},${b|0},${baseA + act * 0.5})`;
  ngCtx.lineWidth = thin ? 1 : 1.5;
  ngCtx.beginPath(); ngCtx.moveTo(x1, y1); ngCtx.quadraticCurveTo(cpx, cpy, x2, y2); ngCtx.stroke();
  if (opts.pulse !== false){                              // travelling signal along the curve
    const t = (orbTime * 0.45 + (opts.seed || (x1 + y1) * 0.0013)) % 1, it = 1 - t;
    const px = it*it*x1 + 2*it*t*cpx + t*t*x2;
    const py = it*it*y1 + 2*it*t*cpy + t*t*y2;
    ngCtx.fillStyle = `rgba(${r|0},${g|0},${b|0},${(thin?0.18:0.3) + act*0.5})`;
    ngCtx.beginPath(); ngCtx.arc(px, py, thin ? 1.2 : 2, 0, Math.PI*2); ngCtx.fill();
  }
}

// Component neuron (outer layer). `vis` 0..1 fades it in; `lbl` toggles label.
function ngDrawChild(x, y, label, color, vis, lbl){
  const [r,g,b] = color;
  const a = 0.22 + vis * 0.65;
  const grd = ngCtx.createRadialGradient(x, y, 0, x, y, 10);
  grd.addColorStop(0, `rgba(${r},${g},${b},${0.5*a})`);
  grd.addColorStop(1, `rgba(${r},${g},${b},0)`);
  ngCtx.fillStyle = grd; ngCtx.beginPath(); ngCtx.arc(x, y, 10, 0, Math.PI*2); ngCtx.fill();
  ngCtx.fillStyle = `rgba(${r},${g},${b},${a})`;
  ngCtx.beginPath(); ngCtx.arc(x, y, 2.6 + vis*1.4, 0, Math.PI*2); ngCtx.fill();
  if (lbl){
    ngCtx.fillStyle = `rgba(234,246,255,${0.5 + vis*0.45})`;
    ngCtx.font = '500 9px "JetBrains Mono", monospace'; ngCtx.textAlign = 'center';
    ngCtx.fillText(label, x, y - 9);
  }
}

function ngDrawNode(n){
  const [r,g,b] = n.color;
  const sel = (n.id === ngSel), hov = (n.id === ngHover);
  const rad = (5 + n.act*9) * (sel ? 1.35 : 1) + (hov ? 1.5 : 0);
  const grd = ngCtx.createRadialGradient(n.x,n.y,0,n.x,n.y,rad*4);
  grd.addColorStop(0, `rgba(${r},${g},${b},${0.45+n.act*0.5+(sel?0.3:0)})`);
  grd.addColorStop(1, `rgba(${r},${g},${b},0)`);
  ngCtx.fillStyle = grd; ngCtx.beginPath(); ngCtx.arc(n.x,n.y,rad*4,0,Math.PI*2); ngCtx.fill();
  ngCtx.fillStyle = `rgba(${r},${g},${b},${0.85+n.act*0.15})`;
  ngCtx.beginPath(); ngCtx.arc(n.x,n.y,rad,0,Math.PI*2); ngCtx.fill();
  if (n.act > 0.05){ ngCtx.strokeStyle=`rgba(${r},${g},${b},${n.act*0.5})`; ngCtx.lineWidth=1.5;
    ngCtx.beginPath(); ngCtx.arc(n.x,n.y, rad+(1-n.act)*22, 0, Math.PI*2); ngCtx.stroke(); }
  if (sel || hov){ ngCtx.strokeStyle=`rgba(${r},${g},${b},${sel?0.9:0.5})`; ngCtx.lineWidth = sel?2:1.5;
    ngCtx.beginPath(); ngCtx.arc(n.x,n.y, rad+8, 0, Math.PI*2); ngCtx.stroke(); }
  ngCtx.fillStyle = `rgba(${sel?255:r},${sel?255:g},${sel?255:b},${0.6+n.act*0.4+(sel?0.2:0)})`;
  ngCtx.font = `${sel?700:600} 9px "JetBrains Mono", monospace`; ngCtx.textAlign='center';
  ngCtx.fillText(n.label, n.x, n.y + rad + 14);
}

function ngDrawCore(cx,cy){
  const [r,g,b] = ngAccent;
  const rad = 26 * (1 + Math.sin(orbTime*1.5)*0.06 + ngCore.act*0.5);
  const grd = ngCtx.createRadialGradient(cx,cy,0,cx,cy,rad*3);
  grd.addColorStop(0, `rgba(${r|0},${g|0},${b|0},${0.4+ngCore.act*0.4})`);
  grd.addColorStop(1, `rgba(${r|0},${g|0},${b|0},0)`);
  ngCtx.fillStyle = grd; ngCtx.beginPath(); ngCtx.arc(cx,cy,rad*3,0,Math.PI*2); ngCtx.fill();
  ngCtx.strokeStyle = `rgba(${r|0},${g|0},${b|0},0.8)`; ngCtx.lineWidth=2;
  ngCtx.beginPath(); ngCtx.arc(cx,cy,rad,0,Math.PI*2); ngCtx.stroke();
  ngCtx.fillStyle = 'rgba(255,255,255,0.92)';
  ngCtx.font = '800 15px Orbitron, "JetBrains Mono", monospace'; ngCtx.textAlign='center'; ngCtx.textBaseline='middle';
  ngCtx.fillText('DEEP', cx, cy); ngCtx.textBaseline='alphabetic';
}

// ===== THREE.JS PARTICLE SPHERE (sprite helper + overlays retained) =====
let orbScene, orbCamera, orbRenderer;
let particleSphere;
let orbTime = 0;
let orbLastTime = performance.now();
let orbPulseSpeed = 1.0;
let orbPulseMin = 0.97, orbPulseMax = 1.03;

const ORB_COLORS = {
  idle:       { r:1.0, g:1.0,  b:1.0  },
  listening:  { r:0.1, g:1.0,  b:1.0  },
  processing: { r:1.0, g:0.55, b:0.05 },
  speaking:   { r:0.75, g:0.2, b:1.0  }
};
let orbColorCurrent = { r:1, g:1, b:1 };

function _makeSprite() {
  const size = 128;
  const c = document.createElement('canvas');
  c.width = size; c.height = size;
  const ctx2 = c.getContext('2d');
  const g = ctx2.createRadialGradient(size/2, size/2, 0, size/2, size/2, size/2);
  g.addColorStop(0,    'rgba(255,255,255,1)');
  g.addColorStop(0.2,  'rgba(200,210,255,0.9)');
  g.addColorStop(0.5,  'rgba(100,120,255,0.4)');
  g.addColorStop(1,    'rgba(0,0,0,0)');
  ctx2.fillStyle = g;
  ctx2.fillRect(0, 0, size, size);
  return new THREE.CanvasTexture(c);
}

function initOrb() {
  const c = document.createElement('canvas');
  c.id = 'deep-graph-canvas';
  // pointer-events:auto so subsystem nodes are clickable. The chat overlay and
  // command bar sit above (higher z-index) with their own events, so only
  // clicks in the empty background reach the graph.
  c.style.cssText = 'position:fixed;top:0;left:0;z-index:0;pointer-events:auto;display:block;background:#000;';
  document.body.insertBefore(c, document.body.firstChild);
  ngCanvas = c; ngCtx = c.getContext('2d');

  const resize = () => {
    ngW = window.innerWidth; ngH = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    c.width = ngW * dpr; c.height = ngH * dpr;
    c.style.width = ngW + 'px'; c.style.height = ngH + 'px';
    ngCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  resize();
  window.addEventListener('resize', resize);

  // Assign each subsystem an angle around the core.
  NG_NODES.forEach((n, i) => { n.angle = (i / NG_NODES.length) * Math.PI * 2 - Math.PI / 2; n.exp = 0; });

  // ── Interaction ──
  ngEnsureDetail();
  c.addEventListener('click', (e) => {
    const hit = ngHitTest(e.clientX, e.clientY);
    if (hit && hit !== 'core'){ (hit === ngSel) ? ngDeselect() : ngSelect(hit); }
    else { ngDeselect(); }                       // core or empty → collapse
  });
  c.addEventListener('mousemove', (e) => {
    const hit = ngHitTest(e.clientX, e.clientY);
    ngHover = (hit && hit !== 'core') ? hit : null;
    c.style.cursor = hit ? 'pointer' : 'default';
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && ngSel) ngDeselect(); });

  setInterval(ngPollEvents, 2000); ngPollEvents();
  setInterval(ngPollMetrics, 5000); ngPollMetrics();
  console.log('[DEEP] Neural graph (interactive) initialised ✓');
}

function animateOrb() {
  requestAnimationFrame(animateOrb);
  if (!ngCtx) return;

  const now = performance.now();
  const dt  = Math.min((now - orbLastTime) / 1000, 0.05);
  orbLastTime = now;
  orbTime += dt;

  // Smooth accent toward current chat-state color
  const tgt = STATE_RGB[state] || STATE_RGB.idle;
  for (let i = 0; i < 3; i++) ngAccent[i] += (tgt[i] - ngAccent[i]) * 0.05;

  // Chat state keeps relevant subsystems lit
  if (state === 'processing') ngActivate('brain', 0.04);
  if (state === 'speaking')  { ngActivate('voice', 0.05); ngActivate('brain', 0.02); }
  if (state === 'listening')   ngActivate('voice', 0.05);

  // Mic amplitude → core pulse  (+ drive the command-bar waveform bars from the
  // real frequency spectrum, split into 5 perceptual bands)
  if (analyserNode && isListening) {
    analyserNode.getByteFrequencyData(analyserData);
    const avg = analyserData.reduce((a, b) => a + b, 0) / analyserData.length;
    orbMicAmplitude += ((avg / 75) - orbMicAmplitude) * 0.28;
    orbMicAmplitude = Math.max(0, Math.min(orbMicAmplitude, 2.5));
    renderWaveformBars(analyserData);
  } else {
    orbMicAmplitude *= 0.87;
  }

  // TTS amplitude → core pulse while DEEP is speaking (voice-reactive core)
  if (ttsAnalyser && currentAudio && !currentAudio.paused) {
    ttsAnalyser.getByteFrequencyData(ttsAnalyserData);
    const avg = ttsAnalyserData.reduce((a, b) => a + b, 0) / ttsAnalyserData.length;
    ttsAmplitude += ((avg / 60) - ttsAmplitude) * 0.3;
    ttsAmplitude = Math.max(0, Math.min(ttsAmplitude, 2.5));
    // Light the VOICE subsystem in sync with speech envelope
    ngActivate('voice', ttsAmplitude * 0.08);
  } else {
    ttsAmplitude *= 0.85;
  }

  const drive = Math.max(orbMicAmplitude, ttsAmplitude);
  ngCore.act = Math.max(ngCore.act, Math.min(1, drive * 0.5));

  // ═══ THE YANTRA — DEEP's living mandala. Sacred geometry that IS the
  // system architecture: a bindu (the self/awareness) at the centre, an
  // 8-petal lotus (ashtadala) whose petals ARE the eight subsystems,
  // interlocking Shiva/Shakti triangles, an astrolabe tick-ring, and the
  // bhupura (temple-gate frame). Thought propagates as light to the bindu. ═══
  const cx = ngW / 2, cy = ngH * 0.46;
  const minWH = Math.min(ngW, ngH);
  const S = minWH;                          // scale base
  const binduR = S * 0.032 * (1 + Math.sin(orbTime * 1.3) * 0.06 + ngCore.act * 0.55);
  const petalIn  = S * 0.085;
  const petalOut = S * 0.215;
  const midRing  = S * 0.255;
  const outerRing= S * 0.305;
  const bhuHalf  = S * 0.365;
  ngCx = cx; ngCy = cy; ngCoreR = binduR;

  if (!ngSel) ngRot += dt * 0.05;          // astrolabe rotation (pauses when a petal is open)
  const rot = ngRot;

  // Petal anchors (static angles so labels stay legible) for hit-test + inspect.
  NG_NODES.forEach(n => {
    n.x = cx + Math.cos(n.angle) * (petalIn + petalOut) * 0.5;
    n.y = cy + Math.sin(n.angle) * (petalIn + petalOut) * 0.5;
    n.act *= 0.97;
    n.exp += (((n.id === ngSel) ? 1 : 0) - n.exp) * 0.18;
  });
  ngCore.act *= 0.96;

  ngCtx.clearRect(0, 0, ngW, ngH);

  // Ambient depth — indigo void deepening to black at the edges.
  const [ar, ag, ab] = ngAccent;
  const vg = ngCtx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(ngW, ngH) * 0.62);
  vg.addColorStop(0,   `rgba(${ar|0},${ag|0},${ab|0},0.055)`);
  vg.addColorStop(0.35,'rgba(28,22,58,0.05)');
  vg.addColorStop(0.7, 'rgba(8,6,20,0.0)');
  vg.addColorStop(1,   'rgba(2,1,6,0.7)');
  ngCtx.fillStyle = vg; ngCtx.fillRect(0, 0, ngW, ngH);

  const GOLD = [232, 185, 116], FAINT = [150, 130, 200];

  // ── Bhupura — the temple-gate frame (3 nested squares + 4 T-gates) ──
  yBhupura(cx, cy, bhuHalf, GOLD, 0.10 + ngCore.act * 0.05);

  // ── Outer concentric rings + rotating astrolabe tick-ring ──
  yRing(cx, cy, outerRing,        GOLD, 0.14, 1);
  yRing(cx, cy, outerRing - 6,    GOLD, 0.07, 1);
  yTicks(cx, cy, midRing, 72, 6,  rot,        GOLD, 0.12);
  yTicks(cx, cy, midRing, 24, 11, rot,        GOLD, 0.20);   // major ticks
  yRing(cx, cy, midRing,          GOLD, 0.12, 1);

  // ── Interlocking Shiva (down) / Shakti (up) triangles — slow counter-rotation ──
  const triR = S * 0.155;
  yTri(cx, cy, triR,        rot * 0.6,  true,  GOLD,  0.10 + ngCore.act * 0.12, 1);
  yTri(cx, cy, triR,       -rot * 0.6,  false, FAINT, 0.10 + ngCore.act * 0.12, 1);
  yTri(cx, cy, triR * 0.66, rot * 0.9,  true,  GOLD,  0.07, 1);
  yTri(cx, cy, triR * 0.66,-rot * 0.9,  false, FAINT, 0.07, 1);

  // ── Radial spokes (faint guide lines bindu → each petal direction) ──
  NG_NODES.forEach(n => {
    const ex = cx + Math.cos(n.angle) * outerRing, ey = cy + Math.sin(n.angle) * outerRing;
    ngCtx.strokeStyle = `rgba(232,185,116,${0.04 + Math.max(n.act, n.exp) * 0.18})`;
    ngCtx.lineWidth = 1;
    ngCtx.beginPath(); ngCtx.moveTo(cx, cy); ngCtx.lineTo(ex, ey); ngCtx.stroke();
  });

  // ── The 8-petal lotus — each petal is a subsystem ──
  const spread = (Math.PI / NG_NODES.length) * 0.92;
  NG_NODES.forEach(n => {
    const glow = Math.max(n.act, n.exp, (n.id === ngHover ? 0.5 : 0));
    yPetal(cx, cy, n.angle, petalIn, petalOut, spread, n.color,
           0.05 + glow * 0.5, 0.22 + glow * 0.65);
  });

  // ── Thought propagation — light travelling petal → bindu when active ──
  NG_NODES.forEach(n => {
    const glow = Math.max(n.act, (n.id === ngHover ? 0.4 : 0));
    if (glow < 0.06) return;
    const [r, g, b] = n.color;
    const t = (orbTime * 0.7 + n.angle) % 1;        // 0 (tip) → 1 (bindu)
    const rr = petalOut - (petalOut - binduR) * t;
    const px = cx + Math.cos(n.angle) * rr, py = cy + Math.sin(n.angle) * rr;
    ngCtx.fillStyle = `rgba(${r},${g},${b},${glow})`;
    ngCtx.beginPath(); ngCtx.arc(px, py, 2 + glow * 2, 0, Math.PI * 2); ngCtx.fill();
  });

  // ── Petal labels (small caps, brighten on activation/hover) ──
  NG_NODES.forEach(n => {
    const glow = Math.max(n.act, n.exp, (n.id === ngHover ? 0.55 : 0));
    const lr = petalOut + S * 0.045;
    const lx = cx + Math.cos(n.angle) * lr, ly = cy + Math.sin(n.angle) * lr;
    const [r, g, b] = n.color;
    const sel = (n.id === ngSel);
    ngCtx.fillStyle = `rgba(${r},${g},${b},${0.4 + glow * 0.55})`;
    ngCtx.font = `${sel ? 600 : 500} 9px "JetBrains Mono", monospace`;
    ngCtx.textAlign = 'center'; ngCtx.textBaseline = 'middle';
    ngCtx.fillText(n.label, lx, ly);
    ngCtx.textBaseline = 'alphabetic';
  });

  // ── Inner ring around the bindu ──
  yRing(cx, cy, petalIn * 0.7, GOLD, 0.18 + ngCore.act * 0.3, 1);

  // ── The bindu — the seat of awareness ──
  const bloom = ngCtx.createRadialGradient(cx, cy, 0, cx, cy, binduR * 4.5);
  bloom.addColorStop(0,  `rgba(245,215,150,${0.45 + ngCore.act * 0.4})`);
  bloom.addColorStop(0.5,`rgba(232,185,116,${0.12 + ngCore.act * 0.18})`);
  bloom.addColorStop(1,  'rgba(232,185,116,0)');
  ngCtx.fillStyle = bloom; ngCtx.beginPath(); ngCtx.arc(cx, cy, binduR * 4.5, 0, Math.PI * 2); ngCtx.fill();
  ngCtx.fillStyle = `rgba(255,244,224,${0.9})`;
  ngCtx.beginPath(); ngCtx.arc(cx, cy, binduR, 0, Math.PI * 2); ngCtx.fill();
  ngCtx.strokeStyle = `rgba(245,215,150,${0.5 + ngCore.act * 0.4})`; ngCtx.lineWidth = 1.5;
  ngCtx.beginPath(); ngCtx.arc(cx, cy, binduR * 1.9, 0, Math.PI * 2); ngCtx.stroke();

  // मनस् — the name, in Devanagari, resting beneath the bindu
  ngCtx.fillStyle = `rgba(232,185,116,${0.5 + ngCore.act * 0.3})`;
  ngCtx.font = '600 17px "Noto Serif Devanagari", "Cormorant Garamond", serif';
  ngCtx.textAlign = 'center'; ngCtx.textBaseline = 'middle';
  ngCtx.fillText('मनस्', cx, cy + binduR * 4.6);
  ngCtx.textBaseline = 'alphabetic';
}

// ── Yantra primitives ────────────────────────────────────────────────────
function yRing(cx, cy, r, col, alpha, lw) {
  const [R, G, B] = col;
  ngCtx.beginPath(); ngCtx.arc(cx, cy, r, 0, Math.PI * 2);
  ngCtx.strokeStyle = `rgba(${R},${G},${B},${alpha})`; ngCtx.lineWidth = lw || 1; ngCtx.stroke();
}

function yTicks(cx, cy, r, count, len, rot, col, alpha) {
  const [R, G, B] = col;
  ngCtx.strokeStyle = `rgba(${R},${G},${B},${alpha})`; ngCtx.lineWidth = 1;
  for (let i = 0; i < count; i++) {
    const a = rot + i / count * Math.PI * 2;
    ngCtx.beginPath();
    ngCtx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
    ngCtx.lineTo(cx + Math.cos(a) * (r + len), cy + Math.sin(a) * (r + len));
    ngCtx.stroke();
  }
}

function yTri(cx, cy, r, rot, up, col, alpha, lw) {
  const [R, G, B] = col;
  const dir = up ? -1 : 1;
  ngCtx.beginPath();
  for (let k = 0; k < 3; k++) {
    const a = rot + dir * (k * 2 * Math.PI / 3) - (Math.PI / 2) * dir;
    const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
    k ? ngCtx.lineTo(x, y) : ngCtx.moveTo(x, y);
  }
  ngCtx.closePath();
  ngCtx.strokeStyle = `rgba(${R},${G},${B},${alpha})`; ngCtx.lineWidth = lw || 1; ngCtx.stroke();
}

function yPetal(cx, cy, ang, rIn, rOut, spread, col, fillA, strokeA) {
  const [R, G, B] = col;
  const tipX = cx + Math.cos(ang) * rOut, tipY = cy + Math.sin(ang) * rOut;
  const baseX = cx + Math.cos(ang) * rIn, baseY = cy + Math.sin(ang) * rIn;
  const a1 = ang - spread, a2 = ang + spread;
  const midR = (rIn + rOut) * 0.58;
  const c1x = cx + Math.cos(a1) * midR, c1y = cy + Math.sin(a1) * midR;
  const c2x = cx + Math.cos(a2) * midR, c2y = cy + Math.sin(a2) * midR;
  ngCtx.beginPath();
  ngCtx.moveTo(baseX, baseY);
  ngCtx.quadraticCurveTo(c1x, c1y, tipX, tipY);
  ngCtx.quadraticCurveTo(c2x, c2y, baseX, baseY);
  ngCtx.closePath();
  if (fillA > 0) {
    const mx = (baseX + tipX) / 2, my = (baseY + tipY) / 2;
    const grd = ngCtx.createRadialGradient(tipX, tipY, 0, mx, my, rOut - rIn);
    grd.addColorStop(0, `rgba(${R},${G},${B},${fillA})`);
    grd.addColorStop(1, `rgba(${R},${G},${B},0)`);
    ngCtx.fillStyle = grd; ngCtx.fill();
  }
  ngCtx.strokeStyle = `rgba(${R},${G},${B},${strokeA})`; ngCtx.lineWidth = 1.2; ngCtx.stroke();
}

function yBhupura(cx, cy, half, col, alpha) {
  const [R, G, B] = col;
  ngCtx.strokeStyle = `rgba(${R},${G},${B},${alpha})`; ngCtx.lineWidth = 1.2;
  for (let s = 0; s < 3; s++) {
    const h = half - s * 9;
    ngCtx.strokeRect(cx - h, cy - h, h * 2, h * 2);
  }
  // T-gates at the midpoint of each side
  const gate = 22, gd = 11;
  ngCtx.strokeRect(cx - gate / 2, cy - half - gd, gate, gd);   // top
  ngCtx.strokeRect(cx - gate / 2, cy + half,      gate, gd);   // bottom
  ngCtx.strokeRect(cx - half - gd, cy - gate / 2, gd, gate);   // left
  ngCtx.strokeRect(cx + half,      cy - gate / 2, gd, gate);   // right
}

function triggerOrbRipple() {
  ngCore.act = 1;
  NG_NODES.forEach(n => { n.act = Math.min(1, n.act + 0.3); });
}

// ===== MOUSE =====
const mouse = { nx: 0, ny: 0 };
document.addEventListener('mousemove', e => {
  mouse.nx = (e.clientX / window.innerWidth  - 0.5) * 2;
  mouse.ny = (e.clientY / window.innerHeight - 0.5) * 2;
});



// ===== TTS ENGINE =====
let ttsEnabled  = false;
let ttsVoice    = null;
let ttsPending  = null;   // accumulate full response text

let ttsBuffer = "";
let currentAudio = null;
let ttsVolume = parseFloat(localStorage.getItem('deep_tts_volume')) || 0.6;
let ttsQueue = [];       // Queue of utterances to speak sequentially
let ttsSpeaking = false; // Is currently speaking?
let ttsTimeoutId = null; // Debounce timer

function initTTS() {
  // We no longer rely on browser SpeechSynthesis for output!
  // Instead, we use the server's high-quality Neural Edge TTS backend.
}

// ── TTS amplitude analyser — drives the voice-reactive core while speaking ──
let ttsAudioCtx = null;
let ttsAnalyser = null;
let ttsAnalyserData = null;
let ttsAmplitude = 0;          // smoothed 0..~2.5, read by animateOrb
const _ttsSourceCache = new WeakMap();

function _attachTTSAnalyser(audio) {
  try {
    if (!ttsAudioCtx) {
      ttsAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
      ttsAnalyser = ttsAudioCtx.createAnalyser();
      ttsAnalyser.fftSize = 256;
      ttsAnalyser.smoothingTimeConstant = 0.7;
      ttsAnalyserData = new Uint8Array(ttsAnalyser.frequencyBinCount);
      ttsAnalyser.connect(ttsAudioCtx.destination);
    }
    if (ttsAudioCtx.state === "suspended") ttsAudioCtx.resume();
    if (!_ttsSourceCache.has(audio)) {
      const src = ttsAudioCtx.createMediaElementSource(audio);
      src.connect(ttsAnalyser);
      _ttsSourceCache.set(audio, src);
    }
  } catch (e) { /* analyser optional — playback still works */ }
}

// Prefetch a sentence's audio as an object URL while earlier sentences play.
// This pipelines synthesis with playback, eliminating the inter-sentence gap.
function _prefetch(item) {
  if (item.urlPromise) return item.urlPromise;
  item.urlPromise = fetch(`/api/tts?text=${encodeURIComponent(item.clean)}`)
    .then(r => { if (!r.ok) throw new Error(`tts ${r.status}`); return r.blob(); })
    .then(b => URL.createObjectURL(b))
    .catch(e => { console.error("TTS prefetch failed:", e); return null; });
  return item.urlPromise;
}

async function _speakNext() {
  if (!ttsEnabled || ttsQueue.length === 0) {
    ttsSpeaking = false;
    return;
  }
  ttsSpeaking = true;
  const item = ttsQueue.shift();
  const { clean, isLast } = item;

  // Kick off prefetch for the NEXT sentence right now, so its audio is
  // buffered and ready by the time this one finishes playing.
  if (ttsQueue.length > 0) _prefetch(ttsQueue[0]);

  const url = await _prefetch(item);
  if (!ttsEnabled) { ttsSpeaking = false; return; }   // muted while fetching
  if (!url) { _speakNext(); return; }                  // fetch failed — skip

  const audio = new Audio(url);
  audio.volume = ttsVolume;
  audio.crossOrigin = "anonymous";
  currentAudio = audio;
  _attachTTSAnalyser(audio);

  const done = () => {
    URL.revokeObjectURL(url);
    currentAudio = null;
    _speakNext();
  };

  audio.onended = () => {
    done();
    if (isLast && handsFreeMode && !isListening && state === "idle") {
      try { recognition.start(); } catch (e) {}
    }
  };
  audio.onerror = done;

  audio.play().catch(e => {
    console.error("Audio play failed:", e);
    done();
  });
}

function speak(text, cancelPrevious = true, isLast = true) {
  if (!ttsEnabled) return;
  
  // Strip markdown symbols for clean speech
  const clean = text
    .replace(/```[\s\S]*?```/g, 'code block')
    .replace(/`[^`]+`/g, '')
    .replace(/[#*_>\[\]()]/g, '')
    .replace(/https?:\/\/\S+/g, 'link')
    .replace(/\n{2,}/g, '. ')
    .replace(/\n/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim();
    
  if (!clean) return;
  
  // Cancel any ongoing speech and flush queue on new message
  if (cancelPrevious) {
    ttsQueue = [];
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
    ttsSpeaking = false;
    if (ttsTimeoutId) { clearTimeout(ttsTimeoutId); ttsTimeoutId = null; }
  }
  
  // Debounce: accumulate short text chunks, flush after a delay
  const item = { clean, isLast };
  ttsQueue.push(item);
  _prefetch(item);   // start synthesis immediately, don't wait for playback turn

  if (ttsTimeoutId) clearTimeout(ttsTimeoutId);
  ttsTimeoutId = setTimeout(() => {
    ttsTimeoutId = null;
    if (!ttsSpeaking) _speakNext();
  }, 60); // brief debounce to batch rapid tokens
}

window.toggleTTS = () => {
  ttsEnabled = !ttsEnabled;
  const btn = document.getElementById('ttsBtn');
  if (btn) {
    btn.style.borderColor = ttsEnabled ? 'rgba(232,185,116,0.7)' : '';
    btn.style.background  = ttsEnabled ? 'rgba(232,185,116,0.15)' : '';
    btn.style.color       = ttsEnabled ? '#e8b974' : '';
    btn.title = ttsEnabled ? 'Voice ON — click to mute' : 'Voice OFF — click to enable';
  }
  if (!ttsEnabled) {
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
    if (handsFreeMode) {
      handsFreeMode = false;
      if (isListening) recognition.stop();
      addMessage("Voice output disabled. Hands-free mode paused.", "ai");
    }
  }
  localStorage.setItem('deep_tts', ttsEnabled ? '1' : '0');
};

// ===== STARTUP BRIEFING =====
async function fetchBriefing() {
  try {
    const r = await fetch('/api/briefing');
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

async function runStartupBriefing() {
  const b = await fetchBriefing();
  if (!b) {
    const h = new Date().getHours();
    const t = h < 12 ? 'morning' : h < 17 ? 'afternoon' : h < 22 ? 'evening' : 'night';
    const fallback = `Good ${t}, Aryan. DEEP is online and ready.`;
    setTimeout(() => { addMessage(fallback, 'ai'); speak(fallback); }, 900);
    return;
  }
  const msg = b.briefing || `Good ${b.time_of_day}, Aryan. It is ${b.time} on ${b.date}. DEEP is ready.`;
  setTimeout(() => { addMessage(msg, 'ai'); speak(msg); }, 900);
}

// ===== WEBSOCKET =====
function connectWebSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws/deep`);
  ws.onopen    = ()   => { wsConnected = true;  updateStatusUI("online"); };
  ws.onmessage = (e)  => handleWSMessage(JSON.parse(e.data));
  ws.onclose   = ()   => { wsConnected = false; setSendLock(false); hideThinking(); updateStatusUI("offline"); setTimeout(connectWebSocket, 3000); };
  ws.onerror   = (e)  => { wsConnected = false; setSendLock(false); hideThinking(); console.error("WS:", e); };
}

// ── Alert surfacing: turn high-signal backend events into toasts ───────────
const ALERT_EVENTS = {
  unknown_tracker_following: { level: "alert", icon: "◬", open: "proximity",
    title: (p) => `Tracker following you: ${p.kind || "unknown"}`, body: (p) => `${p.vendor || ""} · seen ${p.seen_count || "?"}× · ${p.distance_m != null ? "~" + p.distance_m + "m" : ""}` },
  device_unusual_time: { level: "warn", icon: "◷", open: "proximity",
    title: () => "Device at an unusual hour", body: (p) => `${p.name || p.id} — ${p.note || "atypical presence"}` },
  threat_detected: { level: "alert", icon: "⚠", open: "threat",
    title: () => "Threat detected", body: (p) => p.threat_type || p.description || p.message || "unusual activity" },
  audit_integrity_failed: { level: "alert", icon: "⛓", open: "audit",
    title: () => "Audit integrity alert", body: () => "Hash-chain verification failed" },
  unknown_device_detected: { level: "info", icon: "◈", open: "proximity",
    title: () => "New device on network", body: (p) => `${p.ip || p.mac || ""}${p.vendor ? " · " + p.vendor : ""}` },
  open_network_nearby: { level: "info", icon: "≈", open: "proximity",
    title: () => "Open Wi-Fi network nearby", body: (p) => p.ssid || "" },
  correlated_alert: { level: "alert", icon: "◬", open: "threat",
    title: () => "Correlated activity detected", body: (p) => p.summary || (p.signals || []).join(" + ") },
  morning_briefing: { level: "info", icon: "◉", open: null,
    title: () => "Morning briefing", body: (p) => String(p.text || "").slice(0, 110) },
  proactive_suggestion: { level: "info", icon: "✦", open: null,
    title: (p) => p.title || "DEEP suggestion",
    body: (p) => String(p.body || "").slice(0, 140) },
};
const _lastAlertAt = {};
function maybeSurfaceAlert(d) {
  const cfg = ALERT_EVENTS[d && d.type]; if (!cfg) return;
  const now = Date.now(); if (now - (_lastAlertAt[d.type] || 0) < 9000) return; _lastAlertAt[d.type] = now;
  const p = (d.payload) || {};
  try {
    if (window.DeepToast) DeepToast.show({
      level: cfg.level, icon: cfg.icon, title: cfg.title(p), body: cfg.body(p),
      ttl: cfg.level === "alert" ? 13000 : 8000,
      onClick: () => { try { window.HUD && cfg.open && HUD.open(cfg.open); } catch (_) {} },
    });
    if (cfg.level === "alert" && window.DeepMoodSet) DeepMoodSet("alert", 20000);
  } catch (_) {}
}

function handleWSMessage(d) {
  maybeSurfaceAlert(d);
  switch (d.type) {
    case "thinking":
      setState("processing");
      break;
    case "thinking_start":
      startReasoningStream();
      break;
    case "thinking_token":
      appendReasoningToken(d.content);
      break;
    case "thinking_end":
      endReasoningStream();
      break;
    case "reasoning":
      appendReasoningStep(d.step);
      break;
    case "response_start":
      currentStreamMessage = null;
      ttsBuffer = "";
      _turnCitations = [];   // reset sources for this turn
      if (ttsEnabled && currentAudio) { currentAudio.pause(); currentAudio = null; }
      break;
    case "token":         
      appendToken(d.content); 
      if (ttsEnabled) {
        ttsBuffer += d.content;
        // Split by sentence endings (.?!\n)
        const match = ttsBuffer.match(/([.?!]\s+|\n+)/);
        if (match) {
          const idx = match.index + match[0].length;
          const sentence = ttsBuffer.slice(0, idx);
          ttsBuffer = ttsBuffer.slice(idx);
          speak(sentence, false, false);
        }
      }
      break;
    case "response_end":
      hideThinking();
      endReasoningStream();   // close reasoning panel if still open
      setState("idle");
      setSendLock(false);
      if (d.model) setActiveModel(d.model);
      if (currentStreamMessage) {
        const contentEl = currentStreamMessage.querySelector(".token-content");
        const fullText = contentEl?.textContent || "";
        // Format finished message as markdown
        if (contentEl) contentEl.innerHTML = renderRichContent(fullText);
        // Attach source citations harvested from this turn's tool results
        renderCitations(currentStreamMessage);
        // Attach per-response stats badge (latency + tokens + model)
        if (d.latency || d.tokens || d.model) {
          const badge = document.createElement('div');
          badge.className = 'response-stats';
          const parts = [];
          if (d.model) parts.push(`<span class="rs-model">${prettyModel(d.model)}</span>`);
          if (d.latency) parts.push(`${d.latency < 1000 ? d.latency + 'ms' : (d.latency/1000).toFixed(1) + 's'}`);
          if (d.tokens)  parts.push(`${d.tokens} tok`);
          badge.innerHTML = parts.join('<span class="rs-sep"> · </span>');
          currentStreamMessage.appendChild(badge);
        }
        addFeedbackButtons(currentStreamMessage);
        saveToHistory(fullText, "ai");
        currentStreamMessage.classList.remove("streaming");
        currentStreamMessage = null;
        if (ttsEnabled) { speak(ttsBuffer, false, true); ttsBuffer = ""; }
      } else if (ttsEnabled) {
        speak(ttsBuffer, false, true);
        ttsBuffer = "";
      }
      break;

    case "tool_call":
      // Show an inline tool call card in the chat feed
      showToolCallCard(d.tool, d.args, d.call_id);
      break;

    case "tool_result":
      // Mark the matching tool call card as done
      finishToolCallCard(d.call_id);
      break;
    case "error":
      hideThinking();
      setSendLock(false);
      addMessage("Error: " + d.message, "ai");
      setState("idle");
      break;
    case "security_alert":
      handleSecurityAlert(d.payload);
      break;
    case "security_snapshot":
      updateNetworkPanel(d.payload);
      break;
    case "agent_event":
      handleAgentEvent(d.event_type, d.payload);
      break;
    case "research_event":
      handleResearchEvent(d.event_type, d.payload);
      break;
    case "predictive_event":
      handlePredictiveEvent(d.event_type, d.payload);
      break;
    case "evolution_event":
      handleEvolutionEvent(d.event_type, d.payload);
      break;
    case "knowledge_event":
      handleKnowledgeEvent(d.event_type, d.payload);
      break;
    case "plugin_event":
      handlePluginEvent(d.plugin, d.event_type, d.payload);
      break;
  }
}

// ===== TOOL CALL CARDS =====
const _toolCards = {};   // call_id -> DOM element

const TOOL_ICONS = {
  search_web: '🔍', read_file: '📄', write_file: '✍️', list_directory: '📁',
  run_command: '⚡', cyber_scan_network: '🛡', cyber_scan_ports: '🔒',
  manage_task: '✓', get_time: '🕐', home_automation: '🏠',
  default: '⚙',
};

function showToolCallCard(tool, args, callId) {
  const ws_ = document.getElementById("welcome-screen");
  if (ws_) ws_.classList.add("hidden");
  const card = document.createElement("div");
  card.className = "tool-call-card";
  card.dataset.callId = callId || tool;
  const icon = TOOL_ICONS[tool] || TOOL_ICONS.default;
  const argStr = args && typeof args === 'object'
    ? Object.entries(args).map(([k,v]) => `${k}: ${String(v).slice(0,40)}`).join(' · ')
    : '';
  card.innerHTML = `<div class="tool-call-icon">${icon}</div>`
    + `<div class="tool-call-body">`
    +   `<div class="tool-call-label">DEEP · TOOL</div>`
    +   `<div class="tool-call-name">${tool.replace(/_/g,' ')}</div>`
    +   (argStr ? `<div class="tool-call-args">${escapeHtml(argStr)}</div>` : '')
    + `</div>`
    + `<div class="tool-call-spinner"></div>`;
  const cont = document.getElementById("chatContainer");
  if (cont) { cont.appendChild(card); cont.scrollTop = cont.scrollHeight; }
  if (callId) _toolCards[callId] = card;
}

function finishToolCallCard(callId) {
  const card = callId ? _toolCards[callId] : null;
  if (card) {
    card.classList.add("done");
    delete _toolCards[callId];
  }
}

// ===== EXTENDED THINKING / REASONING STREAM =====
let _reasoningEl = null;      // current reasoning panel DOM
let _reasoningBody = null;

function startReasoningStream() {
  const ws_ = document.getElementById("welcome-screen");
  if (ws_) ws_.classList.add("hidden");
  hideThinking();
  const cont = document.getElementById("chatContainer");
  if (!cont) return;
  const panel = document.createElement("div");
  panel.className = "reasoning-panel open";
  panel.innerHTML =
      `<div class="reasoning-header" onclick="this.parentElement.classList.toggle('open')">`
    +   `<span class="reasoning-pulse"></span>`
    +   `<span class="reasoning-title">REASONING</span>`
    +   `<span class="reasoning-chevron">▾</span>`
    + `</div>`
    + `<div class="reasoning-body"></div>`;
  cont.appendChild(panel);
  cont.scrollTop = cont.scrollHeight;
  _reasoningEl = panel;
  _reasoningBody = panel.querySelector(".reasoning-body");
  setState("processing");
}

function appendReasoningToken(t) {
  if (!_reasoningBody) startReasoningStream();
  if (_reasoningBody) {
    _reasoningBody.textContent += t;
    const cont = document.getElementById("chatContainer");
    if (cont) cont.scrollTop = cont.scrollHeight;
  }
}

function endReasoningStream() {
  if (_reasoningEl) {
    _reasoningEl.classList.add("complete");
    _reasoningEl.classList.remove("open");      // auto-collapse when done
    const title = _reasoningEl.querySelector(".reasoning-title");
    if (title) title.textContent = "REASONING · COMPLETE";
  }
  _reasoningEl = null;
  _reasoningBody = null;
}

// ── Structured reasoning steps (route → model → tools → answer) ────────────
function _shortModel(m) {
  if (!m) return "DEEP";
  m = String(m).toLowerCase();
  if (m.includes("70b") || m.includes("groq")) return "70B core";
  if (m.includes("llama3.2") || m.includes("ollama")) return "local core";
  if (m.includes("claude")) return "Claude";
  if (m.includes("gemini")) return "Gemini";
  return String(m).split(":").pop();
}
function _argPreview(a) {
  try {
    if (!a || typeof a !== "object" || !Object.keys(a).length) return "";
    const v = Object.values(a)[0];
    return ` <span class="rs-arg">${escapeHtml(String(v)).slice(0, 44)}</span>`;
  } catch (_) { return ""; }
}
// ── Source citations harvested from tool results during a turn ─────────────
let _turnCitations = [];
function harvestCitations(text) {
  if (!text) return;
  const t = String(text);
  // search-style "N. Title\n   snippet\n   https://url" blocks
  const re = /\d+\.\s*([^\n\r]+)[\s\S]*?(https?:\/\/[^\s)\]]+)/g;
  let m, found = false;
  while ((m = re.exec(t))) { found = true; addCitation(m[1].trim(), m[2].trim()); }
  if (!found) { (t.match(/https?:\/\/[^\s)\]]+/g) || []).forEach((u) => addCitation("", u)); }
}
function addCitation(title, url) {
  url = url.replace(/[.,]+$/, "");
  if (!/^https?:\/\//.test(url)) return;
  if (_turnCitations.some((c) => c.url === url)) return;
  let domain = ""; try { domain = new URL(url).hostname.replace(/^www\./, ""); } catch (_) { domain = url.split("/")[2] || url; }
  _turnCitations.push({ title: title || domain, url: url, domain: domain });
}
function renderCitations(msgEl) {
  if (!msgEl || !_turnCitations.length) return;
  const wrap = document.createElement("div");
  wrap.className = "deep-citations";
  wrap.innerHTML = `<div class="dc-label">SOURCES</div>` + _turnCitations.slice(0, 6).map((c) =>
    `<a class="dc-card" href="${c.url}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(c.url)}">
       <img class="dc-fav" src="https://www.google.com/s2/favicons?domain=${encodeURIComponent(c.domain)}&sz=32" alt="" onerror="this.style.display='none'">
       <span class="dc-txt"><span class="dc-title">${escapeHtml(c.title).slice(0, 60)}</span><span class="dc-dom">${escapeHtml(c.domain)}</span></span>
     </a>`).join("");
  msgEl.appendChild(wrap);
  _turnCitations = [];
}

function appendReasoningStep(step) {
  if (!step) return;
  if (step.t === "tool_result") { try { harvestCitations(step.result); } catch (_) {} }
  if (!_reasoningBody) startReasoningStream();
  if (_reasoningBody && _reasoningBody.classList.contains("reasoning-body")) {
    _reasoningBody.classList.add("rs-structured");   // switch panel to step mode
  }
  if (!_reasoningBody) return;
  const ICON = { route: "⟐", model: "◆", thinking: "✦", tool_call: "⚙", tool_result: "✓", final: "●" };
  const row = document.createElement("div");
  row.className = "rs-step rs-" + (step.t || "model");
  let label = "";
  if (step.t === "route") label = `Routing → <b>${_shortModel(step.model)}</b> · ${escapeHtml(step.reason || "")}`;
  else if (step.t === "model") label = `<b>${_shortModel(step.model)}</b> reasoning${step.loop > 1 ? " · pass " + step.loop : ""}…`;
  else if (step.t === "tool_call") label = `Calling <b>${escapeHtml(step.tool || "")}</b>${_argPreview(step.args)}`;
  else if (step.t === "tool_result") label = `<b>${escapeHtml(step.tool || "")}</b> → ${escapeHtml(String(step.result || "")).slice(0, 130)}`;
  else if (step.t === "final") label = `Answer ready · <b>${_shortModel(step.model)}</b>`;
  else if (step.t === "thinking") label = escapeHtml(String(step.text || "")).slice(0, 220);
  else label = escapeHtml(JSON.stringify(step));
  row.innerHTML = `<span class="rs-ico">${ICON[step.t] || "◆"}</span><span class="rs-txt">${label}</span>`;
  _reasoningBody.appendChild(row);
  requestAnimationFrame(() => row.classList.add("show"));
  const cont = document.getElementById("chatContainer");
  if (cont) cont.scrollTop = cont.scrollHeight;
}
window.appendReasoningStep = appendReasoningStep;

// ===== CHAT =====
const chatContainer = document.getElementById("chatContainer");
const statusDot     = document.getElementById("statusDot");
const statusText    = document.getElementById("statusText");

function setState(s, btn) {
  state = s;

  const map = { idle:"READY", listening:"LISTENING", processing:"PROCESSING", speaking:"RESPONDING" };
  if (statusText) statusText.textContent = map[s] || "READY";
  if (statusDot)  statusDot.className = "sb-dot " + (s === "idle" ? "" : s);

  const stateMap = { idle:0, listening:1, processing:2, speaking:3 };
  document.querySelectorAll(".sp-state").forEach((b, i) => {
    b.classList.toggle("active", i === stateMap[s]);
  });

  if (btn) {
    document.querySelectorAll(".sp-state").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
  }

  // Update orb pulse behaviour per state
  if (s === "processing") {
    orbPulseSpeed = 3.0; orbPulseMin = 0.93; orbPulseMax = 1.07;
  } else if (s === "listening") {
    orbPulseSpeed = 1.8; orbPulseMin = 0.96; orbPulseMax = 1.04;
  } else if (s === "speaking") {
    orbPulseSpeed = 1.4; orbPulseMin = 0.97; orbPulseMax = 1.03;
  } else {
    orbPulseSpeed = 1.0; orbPulseMin = 0.97; orbPulseMax = 1.03;
  }
}

function updateStatusUI(status) {
  if (status === "offline") {
    if (statusDot)  { statusDot.style.background = "#ef4444"; statusDot.style.boxShadow = "0 0 8px #ef4444"; }
    if (statusText) statusText.textContent = "OFFLINE";
  } else {
    if (statusDot)  { statusDot.style.background = ""; statusDot.style.boxShadow = ""; }
  }
}

function addMessage(text, sender, imageUrl) {
  const ws_ = document.getElementById("welcome-screen");
  if (ws_) ws_.classList.add("hidden");
  const div = document.createElement("div");
  div.className = `message ${sender}`;
  const content = sender === "ai" ? renderRichContent(text) : escapeHtml(text).replace(/\n/g, "<br>");
  const imgHtml = imageUrl ? `<img class="msg-image" src="${imageUrl}" alt="attached image">` : "";
  div.innerHTML = `<div class="message-header">${sender === "user" ? "YOU" : "DEEP"}</div><div class="message-content">${imgHtml}${content}</div>`;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  while (chatContainer.children.length > 60) chatContainer.removeChild(chatContainer.firstChild);
  if (sender === "ai") addFeedbackButtons(div);
  saveToHistory(text, sender);
  return div;
}

function showThinking() {
  if (document.getElementById("thinking-indicator")) return;
  const div = document.createElement("div");
  div.className = "message ai thinking";
  div.id = "thinking-indicator";
  div.innerHTML = `<div class="message-header">DEEP</div><div class="thinking-dots"><span></span><span></span><span></span></div>`;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function hideThinking() {
  const el = document.getElementById("thinking-indicator");
  if (el) el.remove();
}

function appendToken(token) {
  hideThinking();
  if (!currentStreamMessage) {
    currentStreamMessage = document.createElement("div");
    currentStreamMessage.className = "message ai streaming";
    currentStreamMessage.innerHTML = `<div class="message-header">DEEP</div><div class="token-content message-content"></div>`;
    chatContainer.appendChild(currentStreamMessage);
    setState("speaking");
  }
  currentStreamMessage.querySelector(".token-content").textContent += token;
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

let _sendLocked = false;
function setSendLock(locked) {
  _sendLocked = locked;
  const btn = document.querySelector(".send-btn");
  const inp = document.getElementById("aiInput");
  if (btn) btn.style.opacity = locked ? "0.4" : "";
  if (inp) inp.disabled = locked;
}

async function sendMessage() {
  if (_sendLocked) return;
  const inp  = document.getElementById("aiInput");
  const text = inp.value.trim();
  // An attached image can be sent with no text (DEEP will just describe it).
  const image = (window.DeepVision && DeepVision.has()) ? DeepVision.consume() : null;
  if (!text && !image) return;

  // Slash-commands only apply to pure-text turns.
  if (!image) {
    const cmd = parseCommand(text);
    if (cmd.handled) {
      addMessage(text, "user");
      addMessage(cmd.response, "ai");
      inp.value = "";
      return;
    }
  }

  addMessage(text, "user", image);
  inp.value = "";
  inp.style.height = "auto";
  currentStreamMessage = null;
  setSendLock(true);
  triggerOrbRipple();
  showThinking();
  const sendBtn = document.querySelector(".send-btn");
  if (sendBtn) { sendBtn.classList.add("sending"); setTimeout(() => sendBtn.classList.remove("sending"), 400); }

  if (wsConnected) {
    ws.send(JSON.stringify({ type: "chat", text, mode: "auto", image }));
  } else {
    await simulateResponse();
  }
}

async function simulateResponse() {
  setState("processing");
  await sleep(1200);
  setState("speaking");
  const r = [
    "All systems nominal. Neural pathways synchronized and ready for your command.",
    "Quantum core analysis complete. Operating at peak efficiency, sir.",
    "Deep learning modules engaged. Processing your query through multiple cognitive layers.",
    "Neural network active. I am fully operational and awaiting your directive."
  ][Math.floor(Math.random() * 4)].split(" ");
  for (const w of r) { appendToken(w + " "); await sleep(65); }
  await sleep(400);
  setState("idle");
  setSendLock(false);
  if (currentStreamMessage) {
    addFeedbackButtons(currentStreamMessage);
    saveToHistory(currentStreamMessage.querySelector(".token-content")?.textContent || "", "ai");
    currentStreamMessage.classList.remove("streaming");
    currentStreamMessage = null;
  }
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// ===== MARKDOWN =====
function escapeHtml(t) {
  return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function renderMarkdown(text) {
  let h = escapeHtml(text);
  h = h.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
        const label = lang ? `<span class="code-lang">${lang}</span>` : '';
        return `<pre>${label}<button class="copy-code-btn" onclick="copyCode(this)">Copy</button><code>${code}</code></pre>`;
      })
      .replace(/^### (.*$)/gim, "<h3>$1</h3>")
      .replace(/^## (.*$)/gim,  "<h2>$1</h2>")
      .replace(/^# (.*$)/gim,   "<h1>$1</h1>")
      .replace(/\*\*\*(.*?)\*\*\*/g, "<strong><em>$1</em></strong>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g,     "<em>$1</em>")
      .replace(/`([^`]+)`/g,     "<code>$1</code>")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
      .replace(/^\d+\. (.*$)/gim, "<li>$1</li>")
      .replace(/^\- (.*$)/gim,   "<li>$1</li>")
      .replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>")
      .replace(/\n\n/g, "</p><p>")
      .replace(/\n/g, "<br>");
  return h;
}

window.copyCode = btn => {
  navigator.clipboard.writeText(btn.nextElementSibling.textContent).then(()=>{
    btn.textContent = "Copied!";
    setTimeout(()=>(btn.textContent="Copy"),2000);
  });
};

// ===== GENERATIVE UI =====
// DEEP can emit ```deep-ui {json}``` blocks. We lift them out of the prose,
// render them as live interactive components, and markdown-render the rest.
function renderRichContent(text) {
  const blocks = [];
  const stripped = text.replace(/```deep-ui\s*\n([\s\S]*?)```/g, (_, json) => {
    try { blocks.push(renderGenerativeBlock(JSON.parse(json.trim()))); }
    catch (e) { blocks.push(`<div class="gen-ui gen-ui-error">⚠ malformed UI block</div>`); }
    return " GENUI ";
  });
  const parts = stripped.split(" GENUI ");
  let html = "";
  parts.forEach((p, i) => {
    if (p.trim()) html += renderMarkdown(p);
    if (i < blocks.length) html += blocks[i];
  });
  return html;
}

function renderGenerativeBlock(spec) {
  const esc = escapeHtml;
  const title = spec.title ? `<div class="gen-ui-title">${esc(spec.title)}</div>` : "";
  switch (spec.kind) {
    case "metrics": {
      const cells = (spec.items||[]).map(it =>
        `<div class="gen-metric"><span class="gen-metric-val">${esc(String(it.value))}</span>` +
        `<span class="gen-metric-label">${esc(it.label||"")}</span></div>`).join("");
      return `<div class="gen-ui gen-metrics-card">${title}<div class="gen-metrics">${cells}</div></div>`;
    }
    case "bars": {
      const items = spec.items||[];
      const max = Math.max(1, ...items.map(it => Number(it.value)||0));
      const rows = items.map(it => {
        const pct = Math.round(((Number(it.value)||0)/max)*100);
        return `<div class="gen-bar-row"><span class="gen-bar-label">${esc(it.label||"")}</span>` +
          `<span class="gen-bar-track"><span class="gen-bar-fill" style="width:${pct}%"></span></span>` +
          `<span class="gen-bar-val">${esc(String(it.value))}</span></div>`;
      }).join("");
      return `<div class="gen-ui gen-bars-card">${title}<div class="gen-bars">${rows}</div></div>`;
    }
    case "table": {
      const head = (spec.columns||[]).map(c => `<th>${esc(String(c))}</th>`).join("");
      const body = (spec.rows||[]).map(r =>
        `<tr>${r.map(c => `<td>${esc(String(c))}</td>`).join("")}</tr>`).join("");
      return `<div class="gen-ui gen-table-card">${title}<table class="gen-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
    }
    case "keyvalue": {
      const rows = (spec.items||[]).map(it =>
        `<div class="gen-kv"><span class="gen-kv-k">${esc(it.k||"")}</span>` +
        `<span class="gen-kv-v">${esc(String(it.v))}</span></div>`).join("");
      return `<div class="gen-ui gen-kv-card">${title}${rows}</div>`;
    }
    case "checklist": {
      const rows = (spec.items||[]).map(it =>
        `<label class="gen-check"><input type="checkbox" ${it.done?"checked":""} onchange="this.parentElement.classList.toggle('done',this.checked)">` +
        `<span>${esc(it.text||"")}</span></label>`).join("");
      return `<div class="gen-ui gen-check-card ${''}">${title}${rows}</div>`;
    }
    default:
      return `<div class="gen-ui gen-ui-error">⚠ unknown UI kind: ${esc(String(spec.kind))}</div>`;
  }
}

// ===== HISTORY =====
function saveToHistory(text, sender) {
  const h = JSON.parse(localStorage.getItem("deep_chat")||"[]");
  h.push({ text, sender, time: Date.now() });
  if (h.length > 80) h.shift();
  localStorage.setItem("deep_chat", JSON.stringify(h));
}

function loadHistory() {
  JSON.parse(localStorage.getItem("deep_chat")||"[]").slice(-20).forEach(m => {
    const div = document.createElement("div");
    div.className = `message ${m.sender}`;
    const c = m.sender === "ai" ? renderRichContent(m.text) : escapeHtml(m.text);
    div.innerHTML = `<div class="message-header">${m.sender === "user" ? "YOU" : "DEEP"}</div><div class="message-content">${c}</div>`;
    chatContainer.appendChild(div);
  });
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// ===== FEEDBACK =====
function addFeedbackButtons(el) {
  const d = document.createElement("div");
  d.className = "feedback-buttons";
  d.innerHTML = `<button class="feedback-btn" onclick="rateResponse(this,'up')">👍</button>
                 <button class="feedback-btn" onclick="rateResponse(this,'down')">👎</button>`;
  el.appendChild(d);
}

window.rateResponse = (btn, r) => {
  const el = btn.closest(".message");
  el.querySelectorAll(".feedback-btn").forEach(b => { b.classList.remove("liked","disliked"); b.disabled = true; });
  btn.classList.add(r === "up" ? "liked" : "disliked");
  if (r === "down") addMessage("I apologize. Could you clarify what you need?","ai");
  const fb = JSON.parse(localStorage.getItem("deep_feedback")||"[]");
  fb.push({ time: Date.now(), r, text: el.textContent.slice(0,120) });
  localStorage.setItem("deep_feedback", JSON.stringify(fb));
};

// ===== TASKS =====
window.toggleTask = el => {
  el.classList.toggle("completed");
  el.querySelector(".task-checkbox").textContent = el.classList.contains("completed") ? "✓" : "";
  saveTasks();
};
function addTask(text) {
  const el = document.createElement("div");
  el.className = "task-item"; el.onclick = () => toggleTask(el);
  el.innerHTML = `<div class="task-checkbox"></div><span>${escapeHtml(text)}</span>`;
  document.getElementById("taskList").appendChild(el); saveTasks();
}
function saveTasks() {
  localStorage.setItem("deep_tasks", JSON.stringify(
    [...document.querySelectorAll(".task-item")].map(el => ({
      text: el.querySelector("span").textContent,
      completed: el.classList.contains("completed")
    }))
  ));
}
function loadTasks() {
  const s = localStorage.getItem("deep_tasks");
  if (!s) return;
  document.getElementById("taskList").innerHTML = "";
  JSON.parse(s).forEach(t => {
    const el = document.createElement("div");
    el.className = "task-item" + (t.completed ? " completed" : "");
    el.onclick = () => toggleTask(el);
    el.innerHTML = `<div class="task-checkbox">${t.completed?"✓":""}</div><span>${escapeHtml(t.text)}</span>`;
    document.getElementById("taskList").appendChild(el);
  });
}

// ===== PROJECT =====
window.editProject = () => {
  const el = document.getElementById("currentProject");
  const n = prompt("Project name:", el.textContent);
  if (n?.trim()) { el.textContent = n.trim(); localStorage.setItem("deep_project", n.trim()); }
};
function loadProject() {
  const s = localStorage.getItem("deep_project");
  if (s) document.getElementById("currentProject").textContent = s;
}

// ===== MEMORY =====
function addToMemory(key, value) {
  const list = document.getElementById("memoryList");
  const ex = list.querySelector(`[data-key="${CSS.escape(key)}"]`);
  if (ex) { ex.textContent = `${key}: ${value}`; }
  else {
    const item = document.createElement("div");
    item.className = "memory-item"; item.dataset.key = key;
    item.textContent = `${key}: ${value}`; list.appendChild(item);
  }
  const m = JSON.parse(localStorage.getItem("deep_memory")||"{}");
  m[key] = value; localStorage.setItem("deep_memory", JSON.stringify(m));
}
function loadMemory() {
  const s = localStorage.getItem("deep_memory");
  if (!s) return;
  const list = document.getElementById("memoryList"); list.innerHTML = "";
  Object.entries(JSON.parse(s)).forEach(([k,v]) => {
    const item = document.createElement("div");
    item.className = "memory-item"; item.dataset.key = k;
    item.textContent = `${k}: ${v}`; list.appendChild(item);
  });
}

// ===== COMMANDS =====
const _timers = [];

function parseCommand(text) {
  const lo = text.toLowerCase().trim();

  // ---- Time & Date ----
  if (/^(what('s| is) (the )?time|time now|current time)/i.test(lo)) {
    return { handled:true, response: `It is currently ${new Date().toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:true})}, sir.` };
  }
  if (/^(what('s| is) (the )?date|today's date|what day is it)/i.test(lo)) {
    return { handled:true, response: `Today is ${new Date().toLocaleDateString('en-US',{weekday:'long',year:'numeric',month:'long',day:'numeric'})}, sir.` };
  }

  // ---- Timer ----
  const timerMatch = lo.match(/set (a )?timer (for )?([\d.]+)\s*(second|minute|hour|sec|min|hr)s?/i);
  if (timerMatch) {
    const amt  = parseFloat(timerMatch[3]);
    const unit = timerMatch[4].toLowerCase();
    const ms   = amt * (unit.startsWith('h') ? 3600000 : unit.startsWith('m') ? 60000 : 1000);
    const label= `${amt} ${unit}${amt !== 1 ? 's' : ''}`;
    const id   = setTimeout(() => {
      const msg = `Timer complete, sir. Your ${label} timer has elapsed.`;
      addMessage(msg, 'ai');
      speak(msg);
    }, ms);
    _timers.push(id);
    return { handled:true, response:`Timer set for ${label}, sir. I will alert you when it's done.` };
  }

  // ---- System status ----
  if (/^(system status|status report|how are you|all systems)/i.test(lo)) {
    fetch('/api/status').then(r=>r.json()).then(d => {
      const msg = `All systems nominal, Aryan. DEEP brain is ${d.brain}, running ${d.model}, latency ${d.latency_ms ? d.latency_ms+'ms' : 'unknown'}. Current time: ${d.time}.`;
      addMessage(msg, 'ai');
      speak(msg);
    }).catch(() => addMessage('Status endpoint unreachable.', 'ai'));
    return { handled:true, response:'' };
  }

  // ---- Web search ----
  const searchMatch = text.match(/^(search (for |the web for )?|look up |google )(.+)/i);
  if (searchMatch) {
    const q = searchMatch[3].trim();
    window.open(`https://www.google.com/search?q=${encodeURIComponent(q)}`, '_blank');
    return { handled:true, response:`Opening a search for "${q}", sir.` };
  }

  // ---- Task management ----
  if (/^(add|create) task /i.test(text)) {
    const t = text.replace(/^(add|create) task /i,'');
    addTask(t); return { handled:true, response:`Task added: "${t}"` };
  }
  if (lo.includes('clear all tasks')) {
    document.getElementById('taskList').innerHTML = ''; localStorage.removeItem('deep_tasks');
    return { handled:true, response:'All tasks cleared, sir.' };
  }

  // ---- Memory ----
  if (/^(remember|note that) /i.test(text)) {
    const note = text.replace(/^(remember|note that) /i,'');
    const m = note.match(/^(.+?)\s+(?:is|are|=)\s+(.+)$/i);
    if (m) { addToMemory(m[1],m[2]); return { handled:true, response:`Remembered: ${m[1]} = ${m[2]}, sir.` }; }
  }
  if (/what do you remember|show memory/i.test(lo)) {
    const mem = JSON.parse(localStorage.getItem('deep_memory')||'{}');
    return { handled:true, response: Object.entries(mem).map(([k,v])=>`• ${k}: ${v}`).join('\n') || 'Memory bank is empty, sir.' };
  }

  // ---- Project ----
  if (/^(set project|change project to) /i.test(text)) {
    const p = text.replace(/^(set project|change project to) /i,'');
    document.getElementById('currentProject').textContent = p;
    localStorage.setItem('deep_project', p);
    return { handled:true, response:`Active project set to "${p}", sir.` };
  }

  // ---- Clear chat ----
  if (/^clear (chat|conversation|history)$/i.test(lo)) {
    chatContainer.innerHTML = ''; localStorage.removeItem('deep_chat');
    return { handled:true, response:'Conversation cleared, sir. A clean slate.' };
  }

  // ---- Calculator ----
  const calcMatch = lo.match(/^(calculate|compute|what is|what's)\s+([\d+\-*/().\s]+)$/i);
  if (calcMatch) {
    try {
      const result = Function('"use strict"; return (' + calcMatch[2] + ')')();
      return { handled:true, response:`That equals **${result}**, sir.` };
    } catch { /* fall through to AI */ }
  }

  return { handled:false };
}

// ===== VOICE (HYBRID / OFFLINE CAPABLE) =====
let mediaRecorder = null;
let audioChunks = [];
let isListening = false;
let handsFreeMode = false;
let audioCtx = null;
let analyserNode = null;
let analyserData = null;
let orbMicAmplitude = 0;
let vadMode = false;
let vadSilenceTimer = null;
const VAD_THRESHOLD = 14;
const VAD_SILENCE_MS = 1600;

async function initVoice() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // Web Audio analyser for amplitude + VAD
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const src = audioCtx.createMediaStreamSource(stream);
    analyserNode = audioCtx.createAnalyser();
    analyserNode.fftSize = 512;
    analyserNode.smoothingTimeConstant = 0.6;
    analyserData = new Uint8Array(analyserNode.frequencyBinCount);
    src.connect(analyserNode);

    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    
    mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };
    
    mediaRecorder.onstart = () => {
      isListening = true;
      audioChunks = [];
      document.getElementById("voiceBtn")?.classList.add("listening");
      document.getElementById("voiceWaveform")?.classList.add("active");
      showTranscriptPreview("listening");
      setState("listening");
    };
    
    mediaRecorder.onstop = async () => {
      isListening = false;
      document.getElementById("voiceBtn")?.classList.remove("listening");
      document.getElementById("voiceWaveform")?.classList.remove("active");
      if (state === "listening") setState("idle");
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      if (audioBlob.size > 0) await processAudio(audioBlob);
      // VAD loop auto-restarts on next utterance when vadMode is active
    };
  } catch (err) {
    console.error("Microphone access denied or failed", err);
  }
}

async function processAudio(blob) {
  showTranscriptPreview("processing");
  const formData = new FormData();
  formData.append("file", blob, "voice.webm");
  try {
    const res = await fetch("/api/transcribe", { method: "POST", body: formData });
    const data = await res.json();
    hideTranscriptPreview();
    if (data.transcript) {
      document.getElementById("aiInput").value = data.transcript;
      if (data.transcript.toLowerCase().replace(/[.,!?]/g, '').trim() === "exit voice mode") {
        handsFreeMode = false; vadMode = false;
        document.getElementById("aiInput").value = "";
        addMessage("Voice mode deactivated.", "ai");
        return;
      }
      sendMessage();
    } else {
      if (vadMode) showTranscriptPreview("ready");
    }
  } catch (e) {
    console.error("Transcription error:", e);
    hideTranscriptPreview();
  }
}

// ===== VAD + TRANSCRIPT PREVIEW =====
function startVADMode() {
  vadMode = true;
  if (audioCtx && audioCtx.state === "suspended") audioCtx.resume();
  showTranscriptPreview("ready");
  vadPoll();
}

function stopVADMode() {
  vadMode = false;
  clearTimeout(vadSilenceTimer);
  hideTranscriptPreview();
}

function vadPoll() {
  if (!vadMode || !analyserNode) return;
  analyserNode.getByteFrequencyData(analyserData);
  const avg = analyserData.reduce((a, b) => a + b, 0) / analyserData.length;
  if (avg > VAD_THRESHOLD) {
    if (!isListening && mediaRecorder && mediaRecorder.state === "inactive" && state === "idle") {
      try { mediaRecorder.start(); } catch(e) {}
    }
    clearTimeout(vadSilenceTimer);
    vadSilenceTimer = setTimeout(() => {
      if (isListening && mediaRecorder.state === "recording") mediaRecorder.stop();
    }, VAD_SILENCE_MS);
  }
  setTimeout(vadPoll, 60);
}

// Map the FFT spectrum onto the 5 command-bar waveform bars. Low bins (voice
// fundamentals) carry the most energy, so we sample logarithmically so every
// bar stays lively rather than the first one pinning to the top.
let _wfBars = null;
function renderWaveformBars(freq) {
  if (!_wfBars) {
    const wrap = document.getElementById("voiceWaveform");
    if (wrap) wrap.classList.add("live");
    _wfBars = wrap ? Array.from(wrap.querySelectorAll("span")) : [];
  }
  if (!_wfBars.length || !freq || !freq.length) return;
  const n = _wfBars.length;
  const N = freq.length;
  for (let i = 0; i < n; i++) {
    const lo = Math.floor(Math.pow(i / n, 1.6) * N);
    const hi = Math.max(lo + 1, Math.floor(Math.pow((i + 1) / n, 1.6) * N));
    let sum = 0;
    for (let k = lo; k < hi; k++) sum += freq[k];
    const v = sum / (hi - lo) / 255;                 // 0..1
    const h = Math.max(0.12, Math.min(1, v * 1.6));  // floor so bars never vanish
    _wfBars[i].style.transform = `scaleY(${h.toFixed(3)})`;
  }
}

function showTranscriptPreview(mode) {
  const el = document.getElementById("transcript-preview");
  if (!el) return;
  el.className = "transcript-preview visible " + mode;
  if (mode === "ready")      el.innerHTML = '<span class="tp-dot"></span> VAD active — speak to send';
  else if (mode === "listening")  el.innerHTML = '<span class="tp-dot pulsing"></span> Listening&hellip;';
  else if (mode === "processing") el.innerHTML = '<span class="tp-dot cyan"></span> Processing speech&hellip;';
}

function hideTranscriptPreview() {
  const el = document.getElementById("transcript-preview");
  if (el) el.className = "transcript-preview";
}

window.toggleVoice = () => {
  if (!mediaRecorder) { alert("Microphone not initialized or denied."); return; }
  if (vadMode || isListening) {
    handsFreeMode = false;
    stopVADMode();
    if (isListening) { try { mediaRecorder.stop(); } catch(e){} }
    addMessage("Voice mode deactivated.", "ai");
  } else {
    handsFreeMode = true;
    document.getElementById("aiInput").value = "";
    addMessage("Voice mode activated — speak freely, I'll listen automatically.", "ai");
    speak("Voice mode activated. I am listening.");
    startVADMode();
  }
};

// ===== FILE UPLOAD =====
function initFileUpload() {
  const overlay = document.getElementById("uploadOverlay");
  const input   = document.getElementById("fileInput");
  document.addEventListener("dragover", e => { e.preventDefault(); overlay?.classList.add("active"); });
  document.addEventListener("dragleave", e => { if (e.target === overlay) overlay.classList.remove("active"); });
  document.addEventListener("drop", e => {
    e.preventDefault(); overlay?.classList.remove("active");
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
  });
  input?.addEventListener("change", e => { if (e.target.files.length) handleFiles(e.target.files); });
}
function handleFiles(files) {
  [...files].forEach(f => {
    const r = new FileReader();
    if (f.type.startsWith("image/")) {
      // Drop an image → DEEP actually LOOKS at it (local LLaVA vision)
      r.onload = async (e) => {
        addMessage(`🖼 ${f.name} — DEEP is looking…`, "user");
        setState("processing");
        try {
          const resp = await fetch("/api/vision/analyze", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: e.target.result, question: "Describe this image in detail. If it's a UI, note any issues; if a chart/diagram, explain it." }),
          });
          const d = await resp.json();
          addMessage(d.analysis || d.error || "I couldn't analyze that image.", "ai");
        } catch (_) {
          addMessage("Vision analysis failed — is the local vision model available?", "ai");
        } finally { setState("idle"); }
      };
      r.readAsDataURL(f);
    } else {
      // Documents → real ingestion: chunk + embed into long-term memory so
      // DEEP can recall them in any future conversation (a true second brain),
      // instead of dumping truncated text into the input box.
      (async () => {
        addMessage(`📎 Ingesting ${f.name} into memory…`, "user");
        setState("processing");
        try {
          const fd = new FormData();
          fd.append("file", f, f.name);
          const resp = await fetch("/api/knowledge/ingest", { method: "POST", body: fd });
          const d = await resp.json();
          if (d.ok) {
            addMessage(`Got it — I've absorbed **${d.source}** (${d.chunks} chunks, ${d.chars.toLocaleString()} chars). Ask me anything about it.`, "ai");
          } else {
            addMessage(`I couldn't ingest that file: ${d.error || "unknown error"}`, "ai");
          }
        } catch (_) {
          addMessage("File ingestion failed — is the knowledge endpoint available?", "ai");
        } finally { setState("idle"); }
      })();
    }
  });
}

// ===== KEYBOARD SHORTCUTS =====
function initKeyboard() {
  const help = document.getElementById("shortcutsHelp");
  let helpVisible = false;
  document.addEventListener("keydown", e => {
    if (e.key === "?" && document.activeElement?.id !== "aiInput") {
      e.preventDefault(); helpVisible = !helpVisible; help?.classList.toggle("visible", helpVisible);
    }
    if (e.key === "Escape") { help?.classList.remove("visible"); helpVisible = false; if (isListening) recognition?.stop(); document.getElementById("sidePanel")?.classList.remove("open"); closeMemoryVault(); }
    if (e.ctrlKey && e.key === "Enter")  { e.preventDefault(); sendMessage(); }
    if (e.ctrlKey && e.key === "b")      { e.preventDefault(); togglePanel(); }
    if (e.ctrlKey && e.key === "n")      { e.preventDefault(); if (confirm("New conversation?")) { chatContainer.innerHTML = ""; localStorage.removeItem("deep_chat"); syncWelcomeScreen(); } }
    if (e.ctrlKey && e.key === "k")      { e.preventDefault(); openCommandPalette(); }
    if (e.ctrlKey && e.shiftKey && e.key === "V") { e.preventDefault(); toggleVoice(); }
    if (e.ctrlKey && e.shiftKey && e.key === "S") { e.preventDefault(); toggleTTS(); }
  });
}
function searchHistory(q) {
  const h = JSON.parse(localStorage.getItem("deep_chat")||"[]");
  const res = h.filter(m => m.text.toLowerCase().includes(q.toLowerCase()));
  if (!res.length) { addMessage(`No results for "${q}"`, "ai"); return; }
  addMessage(`Found ${res.length} match${res.length>1?"es":""} for "${q}":`, "ai");
  res.slice(0,5).forEach(m => addMessage(`[${m.sender}] ${m.text.slice(0,120)}…`, "ai"));
}

// ===== PANEL TOGGLE =====
window.togglePanel = () => document.getElementById("sidePanel")?.classList.toggle("open");

// ===== THEME =====
window.setTheme = t => {
  document.body.className = t === "dark" ? "" : `${t}-theme`;
  document.querySelectorAll(".theme-btn").forEach(b => b.classList.toggle("active", b.dataset.theme === t));
  localStorage.setItem("deep_theme", t);
};
window.setAccentColor = c => {
  // Calm 2026 palette. Default (cyan) = periwinkle, matching base.css tokens.
  const map = { cyan:"#7c93ff", gold:"#9aa9ff", pink:"#c98ad0", indigo:"#7c93ff", green:"#56c596", orange:"#e0a35a", purple:"#9a8cff" };
  const hex = map[c] || map.cyan;
  const m = hex.replace('#','').match(/.{2}/g).map(h => parseInt(h, 16));
  const root = document.documentElement.style;
  root.setProperty("--color-accent-cyan", hex);
  root.setProperty("--color-accent-cyan-rgb", m.join(", "));
  document.querySelectorAll(".color-option").forEach(o => o.classList.toggle("active", o.dataset.color === c));
  localStorage.setItem("deep_accent", c);
};
window.setFontSize = s => {
  document.getElementById("fontSizeValue").textContent = s + "px";
  document.querySelectorAll(".message").forEach(m => (m.style.fontSize = s + "px"));
  localStorage.setItem("deep_fontSize", s);
};
window.setParticleIntensity = v => {
  if (ngCanvas) ngCanvas.style.opacity = v / 100;
  localStorage.setItem("deep_particles", v);
};
window.setGlassIntensity = v => {
  document.querySelectorAll(".side-panel,.input-dock,.top-bar").forEach(el => {
    el.style.backdropFilter = `blur(${20*(v/100)}px)`;
  });
  localStorage.setItem("deep_glass", v);
};

// ===== SECURITY & NETWORK =====
let _securityState = { devices: [], events: [], local_ip: "--", gateway: "--" };

function handleSecurityAlert(payload) {
  // Show toast
  const sev = payload.severity || "info";
  const toast = document.createElement("div");
  toast.className = `security-toast ${sev}`;
  toast.innerHTML = `<div class="security-toast-title">${escapeHtml(payload.title)}</div><div class="security-toast-desc">${escapeHtml(payload.description)}</div>`;
  document.body.appendChild(toast);
  setTimeout(() => { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 8000);

  // Update panel
  const alertsEl = document.getElementById("net-alerts");
  if (alertsEl) {
    const current = parseInt(alertsEl.textContent) || 0;
    alertsEl.textContent = current + 1;
  }
}

async function fetchNetworkStatus() {
  try {
    const r = await fetch("/api/security/status");
    if (!r.ok) return;
    const d = await r.json();
    updateNetworkPanel(d);
  } catch (e) { console.debug("Network status fetch:", e); }
}

function updateNetworkPanel(d) {
  const summary = d.summary || {};
  const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
  el("net-status", d.status === "active" ? "Secure" : d.status);
  el("net-devices", String(summary.total ?? "--"));
  el("net-trusted", String(summary.trusted ?? "--"));
  el("net-unknown", String(summary.unknown ?? "--"));
  el("net-alerts", String(summary.recent_events ?? "--"));
  el("net-ip", d.local_ip || "--");
  _securityState = { ..._securityState, ...d };
}

window.toggleNetworkMap = () => {
  const overlay = document.getElementById("networkMapOverlay");
  if (!overlay) return;
  const isOpen = overlay.classList.contains("visible");
  if (isOpen) {
    overlay.classList.remove("visible");
    if (netMapRenderer) { netMapRunning = false; }
  } else {
    overlay.classList.add("visible");
    initNetworkMap();
    // Request fresh data
    if (ws && wsConnected) ws.send(JSON.stringify({type:"security_snapshot"}));
  }
};

window.toggleAgentSwarm = () => {
  const overlay = document.getElementById("agentSwarmOverlay");
  if (!overlay) return;
  const isOpen = overlay.classList.contains("visible");
  if (isOpen) {
    overlay.classList.remove("visible");
    if (swarmRenderer) { swarmRunning = false; }
  } else {
    overlay.classList.add("visible");
    initAgentSwarm();
  }
};

// ===== NETWORK TOPOLOGY THREE.JS VISUALIZATION =====
let netMapScene, netMapCamera, netMapRenderer, netMapRunning = false;
let netMapNodes = [], netMapEdges = [];

function initNetworkMap() {
  const wrap = document.getElementById("networkMapWrap");
  if (!wrap || netMapRenderer) return;

  netMapScene = new THREE.Scene();
  netMapCamera = new THREE.PerspectiveCamera(60, wrap.clientWidth / wrap.clientHeight, 0.1, 2000);
  netMapCamera.position.z = 500;

  netMapRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  netMapRenderer.setSize(wrap.clientWidth, wrap.clientHeight);
  netMapRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  netMapRenderer.setClearColor(0x000000, 0);
  wrap.appendChild(netMapRenderer.domElement);

  // Central router node
  const centerGeo = new THREE.SphereGeometry(8, 16, 16);
  const centerMat = new THREE.MeshBasicMaterial({ color: 0xffd700 });
  const centerNode = new THREE.Mesh(centerGeo, centerMat);
  netMapScene.add(centerNode);

  // Glow sprite for center
  const glowTex = _makeSprite();
  const glowMat = new THREE.SpriteMaterial({ map: glowTex, color: 0xffd700, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending });
  const glow = new THREE.Sprite(glowMat);
  glow.scale.set(60, 60, 1);
  centerNode.add(glow);

  // Populate from current data
  rebuildNetworkNodes();

  netMapRunning = true;
  animateNetworkMap();

  window.addEventListener("resize", () => {
    if (!netMapRenderer) return;
    const w = wrap.clientWidth, h = wrap.clientHeight;
    netMapCamera.aspect = w / h;
    netMapCamera.updateProjectionMatrix();
    netMapRenderer.setSize(w, h);
  });
}

function rebuildNetworkNodes() {
  if (!netMapScene) return;
  // Remove old device nodes (keep center)
  netMapNodes.forEach(n => netMapScene.remove(n));
  netMapNodes = [];
  netMapEdges.forEach(e => netMapScene.remove(e));
  netMapEdges = [];

  const devices = _securityState.devices || [];
  const count = Math.max(devices.length, 1);
  const radius = 200;

  // Line material
  const edgeMat = new THREE.LineBasicMaterial({ color: 0x334466, transparent: true, opacity: 0.3 });

  devices.forEach((dev, i) => {
    const angle = (i / count) * Math.PI * 2;
    const x = Math.cos(angle) * radius;
    const y = Math.sin(angle) * radius;
    const z = (Math.random() - 0.5) * 40;

    let color = 0x888888;
    if (dev.trust_status === "trusted") color = 0x00ff88;
    else if (dev.trust_status === "blocked") color = 0xff3355;
    else if (dev.is_gateway) color = 0xffd700;

    const geo = new THREE.SphereGeometry(5, 12, 12);
    const mat = new THREE.MeshBasicMaterial({ color });
    const node = new THREE.Mesh(geo, mat);
    node.position.set(x, y, z);
    netMapScene.add(node);
    netMapNodes.push(node);

    // Glow
    const sg = new THREE.SpriteMaterial({
      map: _makeSprite(), color, transparent: true, opacity: 0.3, blending: THREE.AdditiveBlending
    });
    const sglow = new THREE.Sprite(sg);
    sglow.scale.set(30, 30, 1);
    node.add(sglow);

    // Edge to center
    const edgeGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(x, y, z)
    ]);
    const edge = new THREE.Line(edgeGeo, edgeMat.clone());
    edge.material.opacity = 0.15 + Math.random() * 0.15;
    netMapScene.add(edge);
    netMapEdges.push(edge);
  });
}

function animateNetworkMap() {
  if (!netMapRunning || !netMapRenderer) return;
  requestAnimationFrame(animateNetworkMap);
  const t = performance.now() * 0.0005;
  netMapNodes.forEach((n, i) => {
    n.position.y += Math.sin(t + i) * 0.3;
    n.rotation.y += 0.01;
  });
  netMapScene.rotation.y += 0.002;
  netMapRenderer.render(netMapScene, netMapCamera);
}

// ===== AGENT SWARM THREE.JS VISUALIZATION =====
let swarmScene, swarmCamera, swarmRenderer, swarmRunning = false;
let swarmSatellites = [], swarmBeams = [];
const AGENT_COLORS = {
  researcher: 0x00d4ff,
  coder: 0x10b981,
  analyst: 0xf59e0b,
  cybersec: 0xd946ef,
  planner: 0x8b5cf6,
  writer: 0xff6b6b,
  default: 0xaaaaaa
};

function initAgentSwarm() {
  const wrap = document.getElementById("agentSwarmWrap");
  if (!wrap || swarmRenderer) return;

  swarmScene = new THREE.Scene();
  swarmCamera = new THREE.PerspectiveCamera(60, wrap.clientWidth / wrap.clientHeight, 0.1, 2000);
  swarmCamera.position.z = 500;

  swarmRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  swarmRenderer.setSize(wrap.clientWidth, wrap.clientHeight);
  swarmRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  swarmRenderer.setClearColor(0x000000, 0);
  wrap.appendChild(swarmRenderer.domElement);

  // Central DEEP core
  const coreGeo = new THREE.SphereGeometry(20, 24, 24);
  const coreMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const core = new THREE.Mesh(coreGeo, coreMat);
  swarmScene.add(core);

  const cgTex = _makeSprite();
  const cgMat = new THREE.SpriteMaterial({ map: cgTex, color: 0xffffff, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending });
  const cg = new THREE.Sprite(cgMat);
  cg.scale.set(120, 120, 1);
  core.add(cg);

  // Demo satellites (will be replaced by real agents)
  rebuildAgentSatellites();

  swarmRunning = true;
  animateAgentSwarm();

  window.addEventListener("resize", () => {
    if (!swarmRenderer) return;
    const w = wrap.clientWidth, h = wrap.clientHeight;
    swarmCamera.aspect = w / h;
    swarmCamera.updateProjectionMatrix();
    swarmRenderer.setSize(w, h);
  });
}

function rebuildAgentSatellites() {
  if (!swarmScene) return;
  swarmSatellites.forEach(s => swarmScene.remove(s));
  swarmSatellites = [];
  swarmBeams.forEach(b => swarmScene.remove(b));
  swarmBeams = [];

  const agents = _agentSwarmState || [
    { role: "researcher", status: "running", name: "Researcher" },
    { role: "coder", status: "idle", name: "Coder" },
    { role: "analyst", status: "running", name: "Analyst" },
    { role: "cybersec", status: "idle", name: "CyberSec" },
  ];

  const count = agents.length;
  const orbitRadius = 220;

  agents.forEach((agent, i) => {
    const color = AGENT_COLORS[agent.role] || AGENT_COLORS.default;
    const angle = (i / count) * Math.PI * 2;
    const geo = new THREE.SphereGeometry(8, 16, 16);
    const mat = new THREE.MeshBasicMaterial({ color });
    const sat = new THREE.Mesh(geo, mat);

    // Orbit parameters
    sat.userData = {
      angle: angle,
      radius: orbitRadius + Math.random() * 40,
      speed: 0.0003 + Math.random() * 0.0004,
      tilt: (Math.random() - 0.5) * 0.5,
      phase: Math.random() * Math.PI * 2,
      status: agent.status,
      role: agent.role,
    };
    swarmScene.add(sat);
    swarmSatellites.push(sat);

    // Glow
    const sgMat = new THREE.SpriteMaterial({
      map: _makeSprite(), color, transparent: true,
      opacity: agent.status === "running" ? 0.5 : 0.2,
      blending: THREE.AdditiveBlending
    });
    const sg = new THREE.Sprite(sgMat);
    sg.scale.set(50, 50, 1);
    sat.add(sg);

    // Data beam to core
    const beamGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 0, 0) // updated in animation
    ]);
    const beamMat = new THREE.LineBasicMaterial({
      color, transparent: true, opacity: agent.status === "running" ? 0.4 : 0.08
    });
    const beam = new THREE.Line(beamGeo, beamMat);
    beam.userData = { satIndex: i };
    swarmScene.add(beam);
    swarmBeams.push(beam);
  });
}

let _agentSwarmState = [];

function updateAgentSwarm(agents) {
  _agentSwarmState = agents;
  // Update panel list
  const list = document.getElementById("agentList");
  if (list) {
    list.innerHTML = agents.map(a => {
      const color = "#" + (AGENT_COLORS[a.role] || AGENT_COLORS.default).toString(16).padStart(6, "0");
      const cls = a.status;
      return `<div class="agent-item ${cls}"><span class="agent-dot" style="background:${color}"></span><span>${a.name}</span></div>`;
    }).join("");
  }
  rebuildAgentSatellites();
}

function animateAgentSwarm() {
  if (!swarmRunning || !swarmRenderer) return;
  requestAnimationFrame(animateAgentSwarm);
  const t = performance.now() * 0.001;

  swarmSatellites.forEach((sat, i) => {
    const ud = sat.userData;
    ud.angle += ud.speed;
    const r = ud.radius;
    sat.position.x = Math.cos(ud.angle) * r;
    sat.position.y = Math.sin(ud.angle) * r * Math.cos(ud.tilt);
    sat.position.z = Math.sin(ud.angle) * r * Math.sin(ud.tilt) + Math.sin(t * 2 + ud.phase) * 10;

    // Pulse if running
    if (ud.status === "running") {
      const pulse = 1 + Math.sin(t * 4 + ud.phase) * 0.15;
      sat.scale.setScalar(pulse);
    }
  });

  // Update beams
  swarmBeams.forEach((beam, i) => {
    if (!swarmSatellites[i]) return;
    const sat = swarmSatellites[i];
    const positions = beam.geometry.attributes.position.array;
    positions[3] = sat.position.x;
    positions[4] = sat.position.y;
    positions[5] = sat.position.z;
    beam.geometry.attributes.position.needsUpdate = true;
  });

  swarmScene.rotation.y += 0.001;
  swarmRenderer.render(swarmScene, swarmCamera);
}

function handleAgentEvent(eventType, payload) {
  // Refresh agent list from server periodically — events just hint us
  if (eventType === "agent_created" || eventType === "agent_task_start" || eventType === "agent_task_complete") {
    fetchAgentList();
  }
}

async function fetchAgentList() {
  try {
    const r = await fetch("/api/agents");
    if (!r.ok) return;
    const d = await r.json();
    if (d.agents) {
      const agents = d.agents.map(a => ({
        name: a.name,
        role: a.role,
        status: a.status === "running" ? "running" : "idle"
      }));
      updateAgentSwarm(agents);
    }
  } catch (e) { console.debug("Agent list fetch:", e); }
}

// ===== RESEARCH PANEL =====
async function fetchResearchStats() {
  try {
    const r = await fetch("/api/research/stats");
    if (!r.ok) return;
    const d = await r.json();
    const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    el("res-topics", String(d.topics ?? "--"));
    el("res-findings", String(d.total_findings ?? "--"));
    el("res-unread", String(d.unread_findings ?? "--"));
    el("res-24h", String(d.last_24h ?? "--"));
  } catch (e) { console.debug("Research stats fetch:", e); }
}

async function fetchResearchTopics() {
  try {
    const r = await fetch("/api/research/topics");
    if (!r.ok) return;
    const d = await r.json();
    const list = document.getElementById("topicList");
    if (list && d.topics) {
      list.innerHTML = d.topics.map(t =>
        `<div class="topic-item"><span class="topic-dot"></span><span>${escapeHtml(t.name)}</span></div>`
      ).join("");
    }
  } catch (e) { console.debug("Research topics fetch:", e); }
}

function handleResearchEvent(eventType, payload) {
  if (eventType === "topic_scanned" || eventType === "briefing_ready") {
    fetchResearchStats();
    fetchResearchTopics();
  }
  if (eventType === "briefing_ready" && payload) {
    displayBriefing(payload);
  }
}

async function triggerResearchScan() {
  try {
    const r = await fetch("/api/research/scan", { method: "POST" });
    const d = await r.json();
    if (d.success) {
      addMessage("Research scan initiated. Monitoring topics for new findings.", "ai");
      fetchResearchStats();
      fetchResearchTopics();
    }
  } catch (e) { console.error("Research scan:", e); }
}

async function generateBriefing() {
  try {
    const r = await fetch("/api/research/briefing", { method: "POST" });
    const d = await r.json();
    if (d.success && d.briefing) {
      displayBriefing(d.briefing);
    } else {
      addMessage(d.message || "No new findings available for briefing.", "ai");
    }
  } catch (e) { console.error("Briefing generation:", e); }
}

function displayBriefing(briefing) {
  const summary = briefing.summary || "New research findings available.";
  const topics = briefing.topics || {};
  let html = `<div class="briefing-card">
    <div class="briefing-card-header">◢ MORNING BRIEFING — ${new Date(briefing.created_at).toLocaleTimeString()}</div>
    <div class="briefing-card-summary">${escapeHtml(summary)}</div>`;

  for (const [tid, items] of Object.entries(topics)) {
    if (!items || items.length === 0) continue;
    html += `<div class="briefing-topic-group">
      <div class="briefing-topic-title">${escapeHtml(items[0]?.topic_name || tid)}</div>`;
    items.slice(0, 3).forEach(item => {
      html += `<div class="briefing-item">
        <div class="briefing-item-title">${escapeHtml(item.title || "Untitled")}</div>
        <div class="briefing-item-source">${escapeHtml(item.source || "Unknown")} — ${item.keywords_matched?.join(", ") || ""}</div>
      </div>`;
    });
    html += `</div>`;
  }
  html += `</div>`;

  const div = document.createElement("div");
  div.innerHTML = html;
  chatContainer.appendChild(div.firstElementChild);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// ===== PREDICTIVE BANNER =====
let _currentPrediction = null;

function handlePredictiveEvent(eventType, payload) {
  if (eventType === "prediction_ready") {
    showPredictiveBanner(payload);
  }
}

function showPredictiveBanner(prediction) {
  const banner = document.getElementById("predictiveBanner");
  const textEl = document.getElementById("predictiveText");
  const reasonEl = document.getElementById("predictiveReason");
  if (!banner || !textEl) return;
  
  _currentPrediction = prediction;
  textEl.textContent = prediction.suggestion || "...";
  if (reasonEl) reasonEl.textContent = prediction.reason || "";
  
  banner.style.display = "flex";
  banner.classList.remove("hiding");
  
  // Auto-hide after 20 seconds if no response
  setTimeout(() => {
    if (_currentPrediction && _currentPrediction.id === prediction.id) {
      hidePredictiveBanner();
    }
  }, 20000);
}

function hidePredictiveBanner() {
  const banner = document.getElementById("predictiveBanner");
  if (!banner) return;
  banner.classList.add("hiding");
  setTimeout(() => {
    banner.style.display = "none";
    banner.classList.remove("hiding");
    _currentPrediction = null;
  }, 350);
}

async function acceptPrediction() {
  if (!_currentPrediction) return;
  // Execute the suggestion as a message
  const suggestion = _currentPrediction.suggestion.replace(/^Would you like to /, "").replace(/\?$/, "");
  const inp = document.getElementById("aiInput");
  if (inp) {
    inp.value = suggestion;
    sendMessage();
  }
  // Send feedback
  try {
    await fetch("/api/predictive/feedback", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ prediction_id: _currentPrediction.id, accepted: true })
    });
  } catch (e) {}
  hidePredictiveBanner();
}

async function rejectPrediction() {
  if (!_currentPrediction) return;
  try {
    await fetch("/api/predictive/feedback", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ prediction_id: _currentPrediction.id, accepted: false })
    });
  } catch (e) {}
  hidePredictiveBanner();
}

// ===== EVOLUTION PANEL =====
async function fetchEvolutionStats() {
  try {
    const r = await fetch("/api/evolution/stats");
    if (!r.ok) return;
    const d = await r.json();
    const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    el("evo-convs", String(d.total_conversations ?? "--"));
    el("evo-quality", String(d.avg_quality ? d.avg_quality.toFixed(2) : "--"));
    el("evo-variants", String(d.prompt_variants ?? "--"));
    el("evo-lessons", String(d.lessons_learned ?? "--"));
    el("evo-events", String(d.evolution_events ?? "--"));
    
    // Update timeline
    updateEvolutionTimeline(d.current_modifications || []);
  } catch (e) { console.debug("Evolution stats fetch:", e); }
}

function updateEvolutionTimeline(mods) {
  const timeline = document.getElementById("evoTimeline");
  if (!timeline) return;
  let html = '<div class="evo-node active"><span class="evo-dot"></span><span>Base</span></div>';
  mods.forEach(mod => {
    html += `<div class="evo-node"><span class="evo-dot"></span><span>${escapeHtml(mod)}</span></div>`;
  });
  timeline.innerHTML = html;
}

function handleEvolutionEvent(eventType, payload) {
  if (eventType === "system_evolved") {
    triggerOrbEvolutionFlash();
    addMessage("DEEP has evolved. My system prompt has been updated based on our conversations.", "ai");
  }
  fetchEvolutionStats();
}

function triggerOrbEvolutionFlash() {
  const flash = document.getElementById("orbEvolutionFlash");
  if (!flash) return;
  flash.classList.add("active");
  setTimeout(() => flash.classList.remove("active"), 3000);
  
  // Briefly shift orb color
  const oldColors = { ...orbColorCurrent };
  orbColorCurrent = { r: 0, g: 0.83, b: 1 };
  setTimeout(() => { orbColorCurrent = oldColors; }, 2500);
}

async function forceEvolution() {
  try {
    const r = await fetch("/api/evolution/evaluate", { method: "POST" });
    const d = await r.json();
    if (d.success && d.result && d.result.evolved) {
      triggerOrbEvolutionFlash();
      addMessage("Evaluation complete. System prompt evolved with new directives.", "ai");
    } else {
      addMessage("Evaluation complete. No evolution needed at this time.", "ai");
    }
    fetchEvolutionStats();
  } catch (e) { console.error("Force evolution:", e); }
}

async function showEvolutionHistory() {
  try {
    const r = await fetch("/api/evolution/history?limit=5");
    const d = await r.json();
    if (!d.events || d.events.length === 0) {
      addMessage("No evolution events yet. Keep chatting to help me learn!", "ai");
      return;
    }
    let msg = "**Evolution History:**\n\n";
    d.events.forEach(ev => {
      msg += `- **${ev.event_type}** (${new Date(ev.timestamp).toLocaleDateString()}): ${ev.description}\n`;
      if (ev.quality_delta) msg += `  Quality delta: ${ev.quality_delta > 0 ? '+' : ''}${ev.quality_delta.toFixed(3)}\n`;
    });
    addMessage(msg, "ai");
  } catch (e) { console.error("Evolution history:", e); }
}

// ===== KNOWLEDGE GRAPH PANEL =====
async function fetchKnowledgeStats() {
  try {
    const r = await fetch("/api/knowledge/stats");
    if (!r.ok) return;
    const d = await r.json();
    const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    el("kg-entities", String(d.entities ?? "--"));
    el("kg-relations", String(d.relationships ?? "--"));
    const typeCount = d.entity_types ? Object.keys(d.entity_types).length : 0;
    el("kg-types", String(typeCount));
    
    // Update preview nodes
    updateGraphPreview(d.most_connected || []);
  } catch (e) { console.debug("Knowledge stats fetch:", e); }
}

function updateGraphPreview(mostConnected) {
  const preview = document.getElementById("graphPreview");
  if (!preview) return;
  let html = '<div class="graph-node hub"><span class="gn-dot"></span>Aryan</div>';
  mostConnected.slice(0, 5).forEach(node => {
    html += `<div class="graph-node"><span class="gn-dot"></span>${escapeHtml(node.name)}</div>`;
  });
  preview.innerHTML = html;
}

function handleKnowledgeEvent(eventType, payload) {
  if (eventType === "knowledge_added") {
    fetchKnowledgeStats();
  }
}

// Memory side-panel button → opens the full Vault
function showKnowledgeGraph() { openMemoryVault(); }

// ===== MEMORY VAULT — transparent, editable memory =====
let _vaultTimer = null;
function debouncedVaultSearch() {
  clearTimeout(_vaultTimer);
  _vaultTimer = setTimeout(loadVault, 250);
}

// Memory Vault was merged into the floating Memory Graph window (memory-ring.js).
// These shims keep older callers / hotkeys working by routing to that window.
function openMemoryVault() {
  if (window.HUD) { HUD.open("memory-ring"); return; }
  const ov = document.getElementById("memoryVaultOverlay");
  if (ov) { ov.classList.add("visible"); loadVault(); }
}
function closeMemoryVault() {
  if (window.HUD) { HUD.close("memory-ring"); return; }
  const ov = document.getElementById("memoryVaultOverlay");
  if (ov) ov.classList.remove("visible");
}

async function loadVault() {
  const body = document.getElementById("mvBody");
  const q = (document.getElementById("mvSearch")?.value || "").trim();
  try {
    const r = await fetch(`/api/knowledge/vault?q=${encodeURIComponent(q)}`);
    const d = await r.json();
    const st = document.getElementById("mvStats");
    if (st && d.stats) st.textContent = `${d.stats.entities} memories · ${d.stats.relationships} links`;
    if (!d.entities || d.entities.length === 0) {
      body.innerHTML = `<div class="mv-empty">${q ? "No memories match." : "Nothing remembered yet."}</div>`;
      return;
    }
    body.innerHTML = d.entities.map(e => {
      const seen = e.last_seen ? new Date(e.last_seen).toLocaleDateString() : "";
      return `<div class="mv-item" data-name="${escapeHtml(e.name)}">
        <div class="mv-item-main">
          <span class="mv-item-name">${escapeHtml(e.name)}</span>
          <span class="mv-item-type">${escapeHtml(e.type || "fact")}</span>
        </div>
        <div class="mv-item-meta">
          <span title="times referenced">×${e.mention_count ?? 1}</span>
          <span>${seen}</span>
          <button class="mv-forget" title="Forget this" onclick="forgetEntity(this,'${escapeHtml(e.name).replace(/'/g,"\\'")}')">Forget</button>
        </div>
      </div>`;
    }).join("");
  } catch (e) {
    body.innerHTML = `<div class="mv-empty">Could not load memory.</div>`;
    console.error("vault:", e);
  }
}

async function forgetEntity(btn, name) {
  btn.disabled = true; btn.textContent = "…";
  try {
    const r = await fetch(`/api/knowledge/entity/${encodeURIComponent(name)}`, { method: "DELETE" });
    const d = await r.json();
    if (d.success) {
      const item = btn.closest(".mv-item");
      item.classList.add("forgotten");
      setTimeout(() => { item.remove(); loadVault(); }, 300);
    } else { btn.disabled = false; btn.textContent = "Forget"; }
  } catch (e) { btn.disabled = false; btn.textContent = "Forget"; }
}

async function addMemoryFact() {
  const inp = document.getElementById("mvAddInput");
  const text = (inp?.value || "").trim();
  if (!text) return;
  inp.disabled = true;
  try {
    await fetch("/api/knowledge/ingest", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    inp.value = "";
    loadVault();
  } catch (e) { console.error("add fact:", e); }
  finally { inp.disabled = false; inp.focus(); }
}

// ===== WORKSPACE PANEL =====
async function fetchWorkspaceStats() {
  try {
    const r = await fetch("/api/workspace/stats");
    if (!r.ok) return;
    const d = await r.json();
    const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    el("ws-projects", String(d.projects_tracked ?? "--"));
    el("ws-changes", String(d.files_changed_today ?? "--"));
    el("ws-repos", String(d.git_repos ?? "--"));
    
    const activeEl = document.querySelector("#ws-active .sp-mini-val");
    if (activeEl) {
      activeEl.textContent = d.active_project || "None";
    }
  } catch (e) { console.debug("Workspace stats fetch:", e); }
}

function handlePluginEvent(plugin, eventType, payload) {
  if (plugin === "workspace" && eventType === "file_changed") {
    fetchWorkspaceStats();
  }
}

async function showWorkspaceDetails() {
  try {
    const [statsR, projectsR] = await Promise.all([
      fetch("/api/workspace/stats"),
      fetch("/api/workspace/projects")
    ]);
    const stats = await statsR.json();
    const projects = await projectsR.json();
    
    let msg = "**Workspace**\n\n";
    msg += `Projects tracked: ${stats.projects_tracked}\n`;
    msg += `Files changed today: ${stats.files_changed_today}\n`;
    msg += `Git repos: ${stats.git_repos}\n\n`;
    if (stats.active_project) msg += `**Active:** ${escapeHtml(stats.active_project)}\n\n`;
    if (projects.projects && projects.projects.length > 0) {
      msg += "**Recent Projects:**\n";
      projects.projects.slice(0, 5).forEach(p => {
        msg += `- ${escapeHtml(p.name)}`;
        if (p.git_branch) msg += ` (${p.git_branch})`;
        msg += "\n";
      });
    }
    addMessage(msg, "ai");
  } catch (e) { console.error("Workspace details:", e); }
}

// Periodic network status refresh
setInterval(() => { if (document.visibilityState !== "hidden") { fetchNetworkStatus(); fetchAgentList(); fetchResearchStats(); fetchResearchTopics(); fetchEvolutionStats(); fetchKnowledgeStats(); fetchWorkspaceStats(); } }, 10000);

function loadPreferences() {
  setTheme(localStorage.getItem("deep_theme")||"dark");
  setAccentColor(localStorage.getItem("deep_accent")||"cyan");
  const fs = localStorage.getItem("deep_fontSize")||"14";
  const pi = localStorage.getItem("deep_particles")||"100";
  if (document.getElementById("fontSizeSlider")) { document.getElementById("fontSizeSlider").value = fs; setFontSize(fs); }
  if (document.getElementById("particleSlider")) { document.getElementById("particleSlider").value = pi; setParticleIntensity(pi); }
  // Restore TTS state
  if (localStorage.getItem("deep_tts") === "1") toggleTTS();
}

// ===== LIVE METRICS =====
setInterval(() => {
  const tps = Math.floor(Math.random()*200+700);
  ["tokens","tokens-s"].forEach(id => { const el=document.getElementById(id); if(el) el.textContent=tps; });
  const l = document.getElementById("load"); if(l) l.textContent = Math.floor(Math.random()*20+30)+"%";
}, 3000);

setInterval(() => {
  const cl = document.getElementById("clock");
  if(cl) cl.textContent = new Date().toLocaleTimeString("en-US",{hour12:false});
}, 1000);

const _t0 = Date.now();
setInterval(() => {
  const el = document.getElementById("sessionTime");
  if(!el) return;
  const s = Math.floor((Date.now()-_t0)/1000);
  el.textContent = String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0");
}, 1000);

// ===== WELCOME SCREEN =====
window.useChip = (btn) => {
  const inp = document.getElementById("aiInput");
  inp.value = btn.textContent;
  sendMessage();
};

function syncWelcomeScreen() {
  const ws_ = document.getElementById("welcome-screen");
  if (!ws_) return;
  if (chatContainer && chatContainer.children.length > 0) {
    ws_.classList.add("hidden");
  } else {
    ws_.classList.remove("hidden");
  }
}

// ===== COMMAND PALETTE (Ctrl+K) =====
const PALETTE_COMMANDS = [
  { icon:'✨', label:'New conversation', cat:'chat', run:()=>{ chatContainer.innerHTML=''; localStorage.removeItem('deep_chat'); syncWelcomeScreen(); } },
  { icon:'🔊', label:'Toggle voice output (TTS)', cat:'voice', run:()=>toggleTTS() },
  { icon:'🎙', label:'Toggle voice input', cat:'voice', run:()=>toggleVoice() },
  { icon:'⚙', label:'Open / close system panel', cat:'ui', run:()=>togglePanel() },
  { icon:'🛡', label:'View network topology', cat:'security', run:()=>toggleNetworkMap() },
  { icon:'🕸', label:'View agent swarm', cat:'agents', run:()=>toggleAgentSwarm() },
  { icon:'🧠', label:'Show knowledge graph', cat:'memory', run:()=>showKnowledgeGraph() },
  { icon:'📁', label:'Show workspace details', cat:'workspace', run:()=>showWorkspaceDetails() },
  { icon:'🔬', label:'Run research scan', cat:'research', run:()=>triggerResearchScan() },
  { icon:'📰', label:'Generate briefing', cat:'research', run:()=>generateBriefing() },
  { icon:'🧬', label:'Force evolution check', cat:'system', run:()=>forceEvolution() },
  { icon:'🌑', label:'Theme: Dark', cat:'theme', run:()=>setTheme('dark') },
  { icon:'☀', label:'Theme: Light', cat:'theme', run:()=>setTheme('light') },
  { icon:'💡', label:'Theme: Neon', cat:'theme', run:()=>setTheme('neon') },
  { icon:'😴', label:'Enter standby mode', cat:'ui', run:()=>enterStandby() },
  { icon:'◌', label:'Open Memory Ring (knowledge graph)', cat:'hud', run:()=>window.openMemoryRing && window.openMemoryRing() },
  { icon:'>_', label:'Open Terminal', cat:'hud', run:()=>window.openTerminal && window.openTerminal() },
  { icon:'∫', label:'Open Math / Physics simulator', cat:'hud', run:()=>window.openMathSim && window.openMathSim() },
  { icon:'⛨', label:'Open Aegis Shield (security)', cat:'hud', run:()=>window.HUD && window.HUD.open('aegis') },
];
// Add subsystem jumps
NG_NODES.forEach(n => PALETTE_COMMANDS.push({
  icon:'◈', label:'Inspect: ' + n.label, cat:'subsystem', run:()=>{ ngSelect(n.id); }
}));

let _paletteEl = null, _paletteIdx = 0, _paletteFiltered = [];

function ensurePalette() {
  if (_paletteEl) return;
  const ov = document.createElement('div');
  ov.className = 'cmd-palette-overlay';
  ov.innerHTML = `<div class="cmd-palette">
    <input class="cmd-palette-input" id="cmdPaletteInput" placeholder="Type a command or search history…" autocomplete="off">
    <div class="cmd-palette-list" id="cmdPaletteList"></div>
  </div>`;
  document.body.appendChild(ov);
  ov.addEventListener('click', e => { if (e.target === ov) closeCommandPalette(); });
  const input = ov.querySelector('#cmdPaletteInput');
  input.addEventListener('input', () => renderPalette(input.value));
  input.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); _paletteIdx = Math.min(_paletteIdx+1, _paletteFiltered.length-1); renderPaletteActive(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); _paletteIdx = Math.max(_paletteIdx-1, 0); renderPaletteActive(); }
    else if (e.key === 'Enter') { e.preventDefault(); runPaletteItem(_paletteIdx); }
    else if (e.key === 'Escape') { e.preventDefault(); closeCommandPalette(); }
  });
  _paletteEl = ov;
}

function openCommandPalette() {
  ensurePalette();
  _paletteEl.classList.add('visible');
  const input = _paletteEl.querySelector('#cmdPaletteInput');
  input.value = ''; renderPalette(''); input.focus();
}
function closeCommandPalette() { if (_paletteEl) _paletteEl.classList.remove('visible'); }

function renderPalette(q) {
  q = (q || '').toLowerCase().trim();
  _paletteFiltered = q
    ? PALETTE_COMMANDS.filter(c => c.label.toLowerCase().includes(q) || c.cat.includes(q))
    : PALETTE_COMMANDS.slice();
  _paletteIdx = 0;
  const list = _paletteEl.querySelector('#cmdPaletteList');
  if (_paletteFiltered.length === 0) {
    list.innerHTML = `<div class="cmd-palette-empty">Press Enter to search history for “${escapeHtml(q)}”</div>`;
    return;
  }
  list.innerHTML = _paletteFiltered.map((c, i) =>
    `<div class="cmd-palette-item${i===0?' active':''}" data-i="${i}">`
    + `<span class="cpi-icon">${c.icon}</span><span>${escapeHtml(c.label)}</span>`
    + `<span class="cpi-cat">${c.cat}</span></div>`).join('');
  list.querySelectorAll('.cmd-palette-item').forEach(el => {
    el.addEventListener('click', () => runPaletteItem(parseInt(el.dataset.i)));
  });
}
function renderPaletteActive() {
  const items = _paletteEl.querySelectorAll('.cmd-palette-item');
  items.forEach((el, i) => el.classList.toggle('active', i === _paletteIdx));
  items[_paletteIdx]?.scrollIntoView({ block:'nearest' });
}
function runPaletteItem(i) {
  const cmd = _paletteFiltered[i];
  const q = _paletteEl.querySelector('#cmdPaletteInput').value.trim();
  closeCommandPalette();
  if (cmd) { try { cmd.run(); } catch(e){ console.error(e); } }
  else if (q) { searchHistory(q); }
}
window.openCommandPalette = openCommandPalette;

// ===== AMBIENT STANDBY MODE =====
let _standbyEl = null;
let _standbyTimer = null;
let _standbyClockTimer = null;
const STANDBY_IDLE_MS = 90_000;   // enter standby after 90 s of no activity

function ensureStandby() {
  if (_standbyEl) return;
  const ov = document.createElement('div');
  ov.className = 'standby-overlay';
  ov.innerHTML = `
    <div class="standby-clock" id="standbyClock">--:--</div>
    <div class="standby-date" id="standbyDate"></div>
    <div class="standby-next" id="standbyNext"></div>
    <div class="standby-hint">Move or press any key to wake</div>`;
  document.body.appendChild(ov);
  ov.addEventListener('click', exitStandby);
  _standbyEl = ov;
}

function _updateStandbyClock() {
  const now = new Date();
  const c = document.getElementById('standbyClock');
  const d = document.getElementById('standbyDate');
  if (c) c.textContent = now.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' });
  if (d) d.textContent = now.toLocaleDateString([], { weekday:'long', month:'long', day:'numeric' });
}

function enterStandby() {
  ensureStandby();
  _updateStandbyClock();
  // Surface the next predicted action if we have one
  const nextEl = document.getElementById('standbyNext');
  if (nextEl) {
    if (_currentPrediction && _currentPrediction.suggestion) {
      nextEl.innerHTML = `<span class="sn-label">Anticipated</span>${escapeHtml(_currentPrediction.suggestion)}`;
    } else {
      nextEl.innerHTML = `<span class="sn-label">Standing by</span>All systems nominal · awaiting your command`;
    }
  }
  _standbyEl.classList.add('active');
  if (_standbyClockTimer) clearInterval(_standbyClockTimer);
  _standbyClockTimer = setInterval(_updateStandbyClock, 1000);
}

function exitStandby() {
  if (_standbyEl) _standbyEl.classList.remove('active');
  if (_standbyClockTimer) { clearInterval(_standbyClockTimer); _standbyClockTimer = null; }
  resetStandbyTimer();
}

function resetStandbyTimer() {
  if (_standbyTimer) clearTimeout(_standbyTimer);
  if (_standbyEl && _standbyEl.classList.contains('active')) return;
  _standbyTimer = setTimeout(enterStandby, STANDBY_IDLE_MS);
}

function initStandby() {
  ['mousemove','keydown','click','touchstart'].forEach(ev =>
    document.addEventListener(ev, () => {
      if (_standbyEl && _standbyEl.classList.contains('active')) exitStandby();
      else resetStandbyTimer();
    }, { passive:true }));
  resetStandbyTimer();
}
window.enterStandby = enterStandby;

// ===== BOOT SEQUENCE =====
(function runBootSequence(){
  const msgs = [
    'Starting up…',
    'Loading memory…',
    'Connecting subsystems…',
    'Ready',
  ];
  const el = document.getElementById('bootStatus');
  if (!el) return;
  let i = 0;
  const tick = () => { if (el && i < msgs.length) { el.textContent = msgs[i++]; setTimeout(tick, 520); } };
  tick();
})();

// ===== BOOT =====
initOrb();
animateOrb();
connectWebSocket();
initVoice();
initTTS();
initFileUpload();
initKeyboard();
initStandby();
loadHistory();
syncWelcomeScreen();
loadTasks();
loadProject();
loadMemory();
loadPreferences();
runStartupBriefing();

// ===== VIEW SWITCHING (Console / Chat / Neural — single page, no reload) =====
function setView(v){
  if (!['console','chat','neural'].includes(v)) v = 'console';
  document.body.dataset.view = v;
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  try { localStorage.setItem('deep_view', v); } catch(e){}
}
window.setView = setView;
setView(localStorage.getItem('deep_view') || 'console');

// ===== AGENT TASKS — instruct agents & watch their progress =====
async function launchAgentTask(){
  const inp = document.getElementById('agentTaskInput');
  const role = document.getElementById('agentRole')?.value || 'researcher';
  const task = (inp?.value || '').trim();
  if (!task) return;
  inp.value = ''; inp.disabled = true;
  try {
    await fetch('/api/agents/task', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ role, task })
    });
  } catch (e) { console.warn('agent launch failed', e); }
  inp.disabled = false;
  renderAgentTasks();
}
window.launchAgentTask = launchAgentTask;

async function renderAgentTasks(){
  const box = document.getElementById('agentTasks');
  if (!box) return;
  let tasks = [];
  try { const r = await fetch('/api/agents/tasks'); if (r.ok) tasks = (await r.json()).tasks || []; } catch (e) { return; }
  box.innerHTML = tasks.map(t => {
    const st = t.status || 'running';
    const cls = st === 'completed' ? 'done' : (st === 'failed' ? 'failed' : 'running');
    const body = t.result ? escapeHtml(t.result) : (t.error ? escapeHtml(t.error) : '');
    const lat = t.latency_ms ? ` · ${(t.latency_ms / 1000).toFixed(1)}s` : '';
    return `<div class="agent-task ${cls}">
      <div class="agent-task-head">
        <span class="agent-task-role">${escapeHtml(t.role || 'agent')}</span>
        <span class="agent-task-status ${cls}">${st}${lat}</span>
      </div>
      <div class="agent-task-desc">${escapeHtml(t.task || '')}</div>
      ${body ? `<div class="agent-task-result">${body}</div>` : ''}
    </div>`;
  }).join('');
}
window.renderAgentTasks = renderAgentTasks;
setInterval(() => { if (document.getElementById('agentTasks')) renderAgentTasks(); }, 4000);
renderAgentTasks();

// PWA: register service worker (only works on https:// or localhost — secure context)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(() => console.log('[DEEP] PWA service worker registered ✓'))
      .catch(err => console.warn('[DEEP] SW registration skipped:', err.message));
  });
}

// Textarea auto-expand
const _ta = document.getElementById("aiInput");
if (_ta) {
  _ta.addEventListener("input", () => {
    _ta.style.height = "auto";
    _ta.style.height = Math.min(_ta.scrollHeight, 120) + "px";
  });
}

// Global passthrough
window.sendMessage  = sendMessage;
window.setState     = setState;
window.copyCode     = window.copyCode;
window.toggleVoice  = window.toggleVoice;
window.togglePanel  = window.togglePanel;
window.toggleTTS    = window.toggleTTS;
window.forceEvolution = forceEvolution;
window.showEvolutionHistory = showEvolutionHistory;
window.showKnowledgeGraph = showKnowledgeGraph;
window.showWorkspaceDetails = showWorkspaceDetails;
