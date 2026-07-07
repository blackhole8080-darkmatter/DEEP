import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { geoOrthographic, geoPath, geoGraticule10, geoInterpolate, geoDistance, geoCircle } from "d3-geo";
import { select } from "d3-selection";
import { drag } from "d3-drag";
import * as topojson from "topojson-client";
import worldData from "./world.json";

// Extract vector landmasses from the downloaded JSON
const land = topojson.feature(worldData as any, (worldData as any).objects.countries);

// Helper for subsolar point (day/night shadow)
function getSubsolarPoint(): [number, number] {
  const now = new Date();
  const dayOfYear = Math.floor((now.getTime() - new Date(now.getFullYear(), 0, 0).getTime()) / 86400000);
  const declination = -23.44 * Math.cos((360 / 365) * (dayOfYear + 10) * (Math.PI / 180));
  const utcHours = now.getUTCHours() + now.getUTCMinutes() / 60 + now.getUTCSeconds() / 3600;
  const longitude = 180 - (utcHours * 15);
  return [longitude, declination];
}

@customElement("threat-globe")
export class ThreatGlobe extends LitElement {
  @property({ attribute: false }) activity = 0;
  @property({ attribute: false }) status = "idle";
  
  @state() private recentAttacks: { ip: string, country: string, time: string, source?: string, targetCity?: string, targetCountry?: string, method?: string }[] = [];
  @state() private selectedNode: any = null;
  @state() private osintLoading = false;
  @state() private osintData: any = null;
  
  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private raf = 0;
  private w = 0; private h = 0;
  
  // Camera State
  private rotY = 0; 
  private rotX = -15; 
  private scaleMult = 1.0;
  private targetRot: [number, number] | null = null;
  
  private isDragging = false;
  private lastDrag = 0;
  
  // Data
  private nodes: { lat: number, lon: number, size: number, pulse: number, isReal: boolean, ip?: string, country?: string, city?: string, org?: string, source?: string, isServer?: boolean, isBotnet?: boolean, isTor?: boolean }[] = [];
  private impacts: { lat: number, lon: number, age: number }[] = [];
  private satellites: { r: number, speed: number, angle: number, tilt: number }[] = [];
  private cables: { start: [number, number], end: [number, number] }[] = [
    {start: [-74.006, 40.7128], end: [-0.1278, 51.5074]}, // NY to London
    {start: [-74.006, 40.7128], end: [-43.1729, -22.9068]}, // NY to Rio
    {start: [-43.1729, -22.9068], end: [18.4232, -33.9249]}, // Rio to Cape Town
    {start: [-118.2437, 34.0522], end: [139.6917, 35.6895]}, // LA to Tokyo
    {start: [139.6917, 35.6895], end: [151.2093, -33.8688]}, // Tokyo to Sydney
    {start: [151.2093, -33.8688], end: [-118.2437, 34.0522]}, // Sydney to LA
    {start: [-0.1278, 51.5074], end: [55.2708, 25.2048]}, // London to Dubai
    {start: [55.2708, 25.2048], end: [103.8198, 1.3521]}, // Dubai to Singapore
    {start: [103.8198, 1.3521], end: [139.6917, 35.6895]} // Singapore to Tokyo
  ];

  static styles = css`
    :host { display: block; width: 100%; height: 100%; pointer-events: auto; position: relative; }
    canvas { width: 100%; height: 100%; display: block; filter: drop-shadow(0 0 20px rgba(0,255,255,0.15)); cursor: grab; }
    canvas:active { cursor: grabbing; }

    .threat-feed {
      position: absolute; top: 40px; left: 40px; width: 440px;
      background: rgba(4, 8, 16, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 8px;
      padding: 16px; font-family: var(--ds-font-mono, monospace);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); z-index: 10;
    }
    .feed-title {
      color: rgba(0, 255, 255, 0.9); font-size: 0.8rem; letter-spacing: 0.15em;
      border-bottom: 1px solid rgba(0, 255, 255, 0.2); padding-bottom: 8px; margin-bottom: 12px; font-weight: bold;
    }
    .feed-line {
      font-size: 0.75rem; line-height: 1.4; display: flex; flex-direction: column; gap: 4px;
      animation: slide-down 0.3s ease-out forwards; cursor: crosshair;
      padding: 6px; border-radius: 4px; transition: background 0.2s;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .feed-line:hover { background: rgba(0, 255, 255, 0.1); }
    @keyframes slide-down { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
    
    .feed-main { display: flex; gap: 8px; align-items: center; pointer-events: none; }
    .feed-details { display: flex; gap: 8px; align-items: center; padding-left: 2px; font-size: 0.7rem; pointer-events: none; }
    
    .feed-main .time { color: rgba(0, 255, 255, 0.5); }
    .feed-main .source { color: #00ffff; font-size: 0.65rem; }
    .feed-main .method { color: #ffcc00; font-weight: bold; flex: 1; text-align: right; }
    
    .feed-details .attacker { color: #ff003c; font-weight: bold; }
    .feed-details .arrow { color: rgba(255, 255, 255, 0.3); }
    .feed-details .target { color: rgba(255, 255, 255, 0.7); }

    .osint-panel {
      position: absolute; top: 40px; right: 40px; width: 320px;
      background: rgba(20, 0, 0, 0.8); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 0, 60, 0.5); border-radius: 8px;
      padding: 16px; font-family: var(--ds-font-mono, monospace);
      box-shadow: 0 10px 40px rgba(255, 0, 60, 0.2); z-index: 10;
      animation: focus-in 0.3s ease-out;
    }
    @keyframes focus-in { from { opacity: 0; transform: scale(0.95) translateX(20px); } to { opacity: 1; transform: none; } }
    .osint-panel .panel-header {
      color: rgba(255, 0, 60, 1); font-size: 0.8rem; letter-spacing: 0.15em;
      border-bottom: 1px solid rgba(255, 0, 60, 0.4); padding-bottom: 8px; margin-bottom: 16px; font-weight: bold;
    }
    .stat { display: flex; flex-direction: column; margin-bottom: 12px; font-size: 0.75rem; }
    .stat .lbl { color: rgba(255, 255, 255, 0.5); font-size: 0.65rem; letter-spacing: 0.1em; margin-bottom: 2px; }
    .stat .val { color: rgba(0, 255, 255, 0.9); font-size: 0.85rem; }
    .stat .val.red { color: rgba(255, 0, 60, 1); text-shadow: 0 0 8px rgba(255,0,60,0.5); }
    
    .actions { margin-top: 20px; display: flex; justify-content: flex-end; }
    .btn {
      background: rgba(255, 0, 60, 0.15); border: 1px solid rgba(255, 0, 60, 0.4);
      color: #ff003c; padding: 6px 12px; border-radius: 4px;
      font-family: inherit; font-size: 0.7rem; cursor: pointer; text-transform: uppercase; transition: all 0.2s;
    }
    .btn:hover { background: rgba(255, 0, 60, 0.4); color: #fff; box-shadow: 0 0 12px rgba(255,0,60,0.6); }

    .map-legend {
      position: absolute; bottom: 40px; left: 40px;
      background: rgba(4, 8, 16, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 8px;
      padding: 12px 16px; font-family: var(--ds-font-mono, monospace);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); z-index: 10;
      display: flex; flex-direction: column; gap: 8px; pointer-events: none;
    }
    .legend-title {
      color: rgba(255, 255, 255, 0.8); font-size: 0.7rem; letter-spacing: 0.1em;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 6px; margin-bottom: 4px; font-weight: bold;
    }
    .legend-item { display: flex; align-items: center; gap: 10px; font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); }
    .legend-color { width: 12px; height: 12px; border-radius: 50%; box-shadow: 0 0 8px currentColor; }
    .legend-color.attacker { color: rgba(255, 0, 60, 1); background: rgba(255, 0, 60, 0.8); }
    .legend-color.botnet { color: rgba(150, 100, 200, 1); background: rgba(150, 100, 200, 0.8); }
    .legend-color.tor { color: rgba(180, 0, 255, 1); background: rgba(180, 0, 255, 0.8); }
    .legend-color.server { color: rgba(0, 255, 255, 1); background: rgba(0, 255, 255, 0.8); }
    .legend-color.hub { color: rgba(0, 255, 128, 1); background: rgba(0, 255, 128, 0.8); }
    .legend-color.shield { color: rgba(0, 255, 255, 1); border: 1px solid rgba(0,255,255,1); background: transparent; border-radius: 2px; }
    .legend-line { width: 16px; height: 2px; box-shadow: 0 0 5px currentColor; }
    .legend-line.attack-line { color: rgba(255, 0, 60, 0.8); background: rgba(255, 0, 60, 0.8); }
    .legend-line.data-line { color: rgba(0, 255, 255, 0.4); background: rgba(0, 255, 255, 0.4); }
    .legend-line.cable { color: rgba(0, 255, 128, 0.8); background: rgba(0, 255, 128, 0.4); }
  `;

  async firstUpdated() {
    this.canvas = this.renderRoot.querySelector("canvas")!;
    this.ctx = this.canvas.getContext("2d")!;
    
    // Satellites setup
    for(let i=0; i<8; i++) {
       this.satellites.push({
         r: 1.15 + Math.random() * 0.2,
         speed: (Math.random() > 0.5 ? 1 : -1) * (0.005 + Math.random() * 0.015),
         angle: Math.random() * Math.PI * 2,
         tilt: (Math.random() - 0.5) * 60 // degrees latitude offset
       });
    }

    // Interactive Drag Rotation
    select(this.canvas).call(
      drag()
        .on("start", () => { this.isDragging = true; this.targetRot = null; })
        .on("drag", (e) => {
          this.rotY += e.dx * 0.4;
          this.rotX -= e.dy * 0.4;
          this.rotX = Math.max(-90, Math.min(90, this.rotX));
          this.lastDrag = performance.now();
        })
        .on("end", () => { this.isDragging = false; })
    );

    // Zoom on Wheel
    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      this.scaleMult += e.deltaY * -0.001;
      this.scaleMult = Math.max(0.6, Math.min(3.5, this.scaleMult));
      this.targetRot = null; // break tracking lock if user scrolls manually
    });

    // Node Clicking (OSINT Targeting)
    this.canvas.addEventListener("click", (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      let closest = null;
      let minDist = 20; // click radius in screen pixels
      
      const cx = this.w / 2;
      const cy = this.h / 2;
      const R = Math.min(this.w, this.h) * 0.40 * this.scaleMult;
      const projection = geoOrthographic().scale(R).translate([cx, cy]).rotate([this.rotY, this.rotX, 0]);
      
      for (const node of this.nodes) {
         if (!node.isReal) continue;
         // Check if node is on the front hemisphere
         if (geoDistance([-this.rotY, -this.rotX], [node.lon, node.lat]) > Math.PI / 2) continue;
         
         const p = projection([node.lon, node.lat]);
         if (!p) continue;
         
         const dist = Math.hypot(p[0] - x, p[1] - y);
         if (dist < minDist) {
           minDist = dist;
           closest = node;
         }
      }
      
      if (closest) {
        this._focusThreat(closest);
      } else {
        this.selectedNode = null;
        this.targetRot = null;
      }
    });
    
    // Seed noise nodes and botnet swarms
    for(let i=0; i<150; i++) {
      const isBotnet = Math.random() > 0.6;
      this.nodes.push({
        lat: (Math.random() - 0.5) * 160,
        lon: (Math.random() - 0.5) * 360,
        size: isBotnet ? (Math.random() * 0.8 + 0.3) : (Math.random() * 1.5 + 0.5),
        pulse: Math.random() * Math.PI * 2,
        isReal: false,
        isBotnet: isBotnet
      });
    }

    try {
      const res = await fetch("/api/threats/live");
      const threats = await res.json();
      if (threats && threats.length > 0) {
        for (const t of threats) {
          this.nodes.push({
            lat: t.lat,
            lon: t.lon,
            size: 3.5,
            pulse: Math.random() * Math.PI * 2,
            isReal: true,
            ip: t.ip,
            country: t.country || t.countryCode || "UNKNOWN",
            city: t.city || "Unknown City",
            org: t.org || "Unknown ISP",
            source: t.source || "SANS ISC"
          });
        }
      }
    } catch(e) { console.error("Failed to fetch live threats", e); }

    try {
      const res = await fetch("/api/servers/live");
      const servers = await res.json();
      if (servers && servers.length > 0) {
        for (const s of servers) {
          this.nodes.push({
            lat: s.lat,
            lon: s.lon,
            size: s.type === "Hub" ? 4.5 : 2.5,
            pulse: Math.random() * Math.PI * 2,
            isReal: true,
            ip: s.ip,
            country: s.country,
            city: s.city,
            org: s.org,
            source: s.type,
            isServer: true,
            isTor: Math.random() > 0.85 && s.type !== "Hub"
          });
        }
      }
    } catch(e) { console.error("Failed to fetch live servers", e); }

    // Simulate real-time streaming to the UI feed
    setInterval(() => {
      if (this.nodes.length > 0) {
        const realNodes = this.nodes.filter(n => n.isReal);
        if (realNodes.length > 1) {
          const attacker = realNodes[Math.floor(Math.random() * realNodes.length)];
          let target = realNodes[Math.floor(Math.random() * realNodes.length)];
          while(target === attacker) target = realNodes[Math.floor(Math.random() * realNodes.length)];
          
          const d = new Date();
          const time = `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}:${d.getSeconds().toString().padStart(2,'0')}`;
          
          const methods = ["SSH Brute Force (tcp/22)", "RDP Exploit (tcp/3389)", "Telnet Scan (tcp/23)", "DDoS Amplification", "HTTP Exploit (tcp/80)", "HTTPS Scan (tcp/443)", "SQLi Payload (tcp/3306)", "Mirai Botnet Scan", "Ransomware Delivery"];
          const method = methods[Math.floor(Math.random() * methods.length)];
          
          this.recentAttacks = [{ 
            ip: attacker.ip || "UNKNOWN", 
            country: attacker.country || "UNK", 
            time, 
            source: attacker.source || "SANS ISC",
            targetCity: target.city || "Unknown City",
            targetCountry: target.country || "Unknown Region",
            method: method
          }, ...this.recentAttacks].slice(0, 6); // keep 6 so it doesn't overflow the UI
        }
      }
    }, 2500);

    new ResizeObserver(() => this._resize()).observe(this);
    this.raf = requestAnimationFrame((ts) => this._loop(ts));
  }

  private async _focusThreat(nodeOrAttack: any) {
    const node = this.nodes.find(n => n.ip === nodeOrAttack.ip);
    if (node) {
      this.selectedNode = node;
      // Auto-tracking: rotate globe to center the node
      this.targetRot = [-node.lon, -node.lat];
      
      this.osintLoading = true;
      this.osintData = null;
      try {
        const res = await fetch(`/api/threats/osint?ip=${node.ip}`);
        this.osintData = await res.json();
      } catch (e) {
        console.error("OSINT fetch failed", e);
      } finally {
        this.osintLoading = false;
      }
    }
  }

  private _resize() {
    if (!this.canvas) return;
    this.w = this.clientWidth || window.innerWidth;
    this.h = this.clientHeight || window.innerHeight;
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = this.w * dpr; 
    this.canvas.height = this.h * dpr;
    this.ctx.scale(dpr, dpr);
  }

  private _loop(ts: number) {
    this.raf = requestAnimationFrame((t) => this._loop(t));
    if (!this.ctx) return;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.w, this.h);
    
    // Auto Rotation / Tracking Lerp
    if (this.targetRot) {
      // Smoothly interpolate towards target
      this.rotY += (this.targetRot[0] - this.rotY) * 0.05;
      this.rotX += (this.targetRot[1] - this.rotX) * 0.05;
      this.scaleMult += (1.8 - this.scaleMult) * 0.05; // Auto-zoom
    } else if (!this.isDragging && (performance.now() - this.lastDrag > 3000)) {
       // Idle rotation
       this.rotY -= (this.status === 'thinking' ? 0.8 : 0.2) + this.activity * 0.2;
    }
    
    const cx = this.w / 2;
    const cy = this.h / 2;
    const R = Math.min(this.w, this.h) * 0.40 * this.scaleMult;
    
    // Configure D3 Geographic Projection
    const projection = geoOrthographic().scale(R).translate([cx, cy]).rotate([this.rotY, this.rotX, 0]);
    const path = geoPath(projection, ctx);
    
    // 1. Atmosphere Radial Glow
    const atm = ctx.createRadialGradient(cx, cy, R*0.8, cx, cy, R*1.4);
    if (this.status === 'warning') atm.addColorStop(0, 'rgba(255, 0, 60, 0.15)');
    else if (this.status === 'thinking') atm.addColorStop(0, 'rgba(0, 255, 65, 0.15)');
    else atm.addColorStop(0, 'rgba(0, 255, 255, 0.1)');
    atm.addColorStop(1, 'transparent');
    ctx.fillStyle = atm;
    ctx.fillRect(0,0, this.w, this.h);

    let baseColor = 'rgba(0, 255, 255, 0.2)';
    let landColor = 'rgba(0, 255, 255, 0.05)';
    let brightColor = 'rgba(0, 255, 255, 0.9)';
    if (this.status === 'warning') {
      baseColor = 'rgba(255, 0, 60, 0.3)';
      landColor = 'rgba(255, 0, 60, 0.08)';
      brightColor = 'rgba(255, 0, 60, 1.0)';
    } else if (this.status === 'thinking') {
      baseColor = 'rgba(0, 255, 65, 0.3)';
      landColor = 'rgba(0, 255, 65, 0.08)';
      brightColor = 'rgba(0, 255, 65, 1.0)';
    }
    
    // 2. Draw Deep Ocean Background
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(1, 2, 5, 0.8)';
    ctx.fill();

    // 3. Global Heatmap (Summing faint glowing circles at real nodes)
    ctx.globalCompositeOperation = "lighter";
    const realNodes = this.nodes.filter(n => n.isReal);
    for (const node of realNodes) {
      if (geoDistance([-this.rotY, -this.rotX], [node.lon, node.lat]) > Math.PI/2) continue; // backface cull
      const p = projection([node.lon, node.lat]);
      if (!p) continue;
      
      const grad = ctx.createRadialGradient(p[0], p[1], 0, p[0], p[1], R * 0.25);
      grad.addColorStop(0, "rgba(255, 0, 60, 0.06)");
      grad.addColorStop(1, "rgba(255, 0, 60, 0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p[0], p[1], R * 0.25, 0, Math.PI*2);
      ctx.fill();
    }
    ctx.globalCompositeOperation = "source-over";

    // 4. Draw Graticule (Lat/Lon grid)
    ctx.beginPath();
    path(geoGraticule10());
    ctx.strokeStyle = 'rgba(0, 255, 255, 0.06)';
    ctx.lineWidth = 0.5;
    ctx.stroke();

    // 4.5 Draw Undersea Cables
    ctx.globalAlpha = 0.8;
    for (const cable of this.cables) {
        const interpolator = geoInterpolate(cable.start, cable.end);
        const lineCoords = [];
        for(let i=0; i<=1.0; i+=0.05) lineCoords.push(interpolator(i));
        
        let visible = false;
        for (const coord of lineCoords) {
           if (geoDistance([-this.rotY, -this.rotX], [coord[0], coord[1]]) <= Math.PI/2) { visible = true; break; }
        }
        if (visible) {
            ctx.beginPath();
            path({type: "LineString", coordinates: lineCoords});
            ctx.strokeStyle = 'rgba(0, 255, 128, 0.6)';
            ctx.lineWidth = 1.5;
            ctx.stroke();
        }
    }
    ctx.globalAlpha = 1.0;

    // 5. Draw World Landmasses (Continents) with National DefCon Heatmaps
    const features = (land as any).features || [(land as any)];
    for (let i = 0; i < features.length; i++) {
      const feature = features[i];
      ctx.beginPath();
      path(feature);
      
      const heatHash = (i * 13) % 100;
      let fill = landColor;
      if (heatHash < 5) fill = 'rgba(255, 0, 60, 0.15)'; // High Threat
      else if (heatHash < 15) fill = 'rgba(255, 128, 0, 0.1)'; // Med Threat
      
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.strokeStyle = baseColor;
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // 6. Day/Night Cycle (Terminator Shadow)
    const subsolar = getSubsolarPoint();
    const antipode: [number, number] = [subsolar[0] > 0 ? subsolar[0] - 180 : subsolar[0] + 180, -subsolar[1]];
    const nightCircle = geoCircle().center(antipode).radius(90)();
    ctx.beginPath();
    path(nightCircle);
    ctx.fillStyle = "rgba(0, 0, 5, 0.6)"; // Deep night shadow
    ctx.fill();

    // 7. Target Nodes & Selection Reticle
    ctx.globalCompositeOperation = 'lighter';
    for (const node of this.nodes) {
       const pulse = (Math.sin(ts * 0.004 + node.pulse) + 1) / 2;
       
       if (node.isReal && geoDistance([-this.rotY, -this.rotX], [node.lon, node.lat]) > Math.PI/2) continue;

       ctx.beginPath();
       path.pointRadius(node.size + pulse * 1.5);
       path({type: "Point", coordinates: [node.lon, node.lat]});
       
       if (node.isReal) {
         if (node.isTor) {
           ctx.fillStyle = 'rgba(180, 0, 255, 1.0)';
           ctx.globalAlpha = 0.8 + pulse * 0.2;
         } else if (node.isServer) {
           if (node.source === 'Hub') ctx.fillStyle = 'rgba(0, 255, 128, 1.0)';
           else if (node.source === 'Mobile Tower') ctx.fillStyle = 'rgba(255, 150, 0, 1.0)';
           else if (node.source === 'IXP') ctx.fillStyle = 'rgba(255, 0, 150, 1.0)';
           else if (node.source === 'Datacenter') ctx.fillStyle = 'rgba(50, 150, 255, 1.0)';
           else ctx.fillStyle = 'rgba(0, 255, 255, 1.0)';
           ctx.globalAlpha = 0.8 + pulse * 0.2;
         } else {
           ctx.fillStyle = 'rgba(255, 0, 60, 1.0)';
           ctx.globalAlpha = 0.6 + pulse * 0.4;
         }
       } else {
         if (node.isBotnet) {
           ctx.fillStyle = 'rgba(150, 100, 200, 0.8)';
           ctx.globalAlpha = 0.3 + pulse * 0.4;
         } else {
           ctx.fillStyle = brightColor;
           ctx.globalAlpha = 0.2 + pulse * 0.5;
         }
       }
       ctx.fill();

       if (node.isReal && node.isServer && node.source === 'Mobile Tower') {
           const p = projection([node.lon, node.lat]);
           if (p) {
               ctx.beginPath();
               ctx.arc(p[0], p[1], node.size + pulse * 4 + 2, -Math.PI/4, Math.PI/4);
               ctx.strokeStyle = `rgba(255, 150, 0, ${(1 - pulse) * 0.8})`;
               ctx.lineWidth = 1;
               ctx.stroke();
               ctx.beginPath();
               ctx.arc(p[0], p[1], node.size + pulse * 8 + 4, -Math.PI/4, Math.PI/4);
               ctx.strokeStyle = `rgba(255, 150, 0, ${(1 - pulse) * 0.4})`;
               ctx.lineWidth = 0.5;
               ctx.stroke();
           }
       }

       // Draw Reticle if selected
       if (this.selectedNode === node) {
         const p = projection([node.lon, node.lat]);
         if (p) {
           ctx.beginPath();
           ctx.arc(p[0], p[1], 15 + pulse * 5, 0, Math.PI*2);
           ctx.strokeStyle = "#ff003c";
           ctx.lineWidth = 1.5;
           ctx.setLineDash([4, 4]);
           ctx.stroke();
           ctx.setLineDash([]);
           
           // Connecting line to OSINT panel
           ctx.beginPath();
           ctx.moveTo(p[0] + 15, p[1]);
           ctx.lineTo(p[0] + 80, p[1] - 80);
           ctx.lineTo(this.w - 360, p[1] - 80);
           ctx.strokeStyle = "rgba(255, 0, 60, 0.4)";
           ctx.stroke();
         }
       }
    }
    ctx.globalAlpha = 1.0;
    ctx.globalCompositeOperation = 'source-over';

    // 8. Orbiting Satellites
    for (const sat of this.satellites) {
      sat.angle += sat.speed;
      const satLon = (sat.angle * 180 / Math.PI) % 360;
      const satLat = sat.tilt;
      
      if (geoDistance([-this.rotY, -this.rotX], [satLon, satLat]) > Math.PI/2) continue; // Behind globe
      
      const satProj = geoOrthographic().scale(R * sat.r).translate([cx, cy]).rotate([this.rotY, this.rotX, 0]);
      const pSat = satProj([satLon, satLat]);
      const pSurf = projection([satLon, satLat]);
      
      if (pSat && pSurf) {
         ctx.beginPath();
         ctx.moveTo(pSurf[0], pSurf[1]);
         ctx.lineTo(pSat[0], pSat[1]);
         ctx.strokeStyle = "rgba(0, 255, 255, 0.15)";
         ctx.lineWidth = 1;
         ctx.stroke();
         
         ctx.beginPath();
         ctx.arc(pSat[0], pSat[1], 2, 0, Math.PI*2);
         ctx.fillStyle = "#fff";
         ctx.shadowBlur = 8;
         ctx.shadowColor = "#00ffff";
         ctx.fill();
         ctx.shadowBlur = 0;
         
         // Laser Relay to nearest hub if in front
         const hubs = this.nodes.filter(n => n.source === 'Hub');
         if (hubs.length > 0) {
             const hub = hubs[Math.floor(Math.abs(sat.angle * 10)) % hubs.length];
             if (geoDistance([-this.rotY, -this.rotX], [hub.lon, hub.lat]) <= Math.PI/2) {
                 const pHub = projection([hub.lon, hub.lat]);
                 if (pHub) {
                     ctx.beginPath();
                     ctx.moveTo(pSat[0], pSat[1]);
                     ctx.lineTo(pHub[0], pHub[1]);
                     ctx.strokeStyle = "rgba(0, 255, 128, 0.2)";
                     ctx.lineWidth = 0.5;
                     ctx.setLineDash([2, 4]);
                     ctx.stroke();
                     ctx.setLineDash([]);
                 }
             }
         }
      }
    }

    // 8.5 Draw Server Connections
    const servers = this.nodes.filter(n => n.isServer);
    const hubs = servers.filter(s => s.source === 'Hub');
    const edges = servers.filter(s => s.source !== 'Hub');
    
    ctx.globalAlpha = 0.6;
    for (const s of edges) {
        if (hubs.length === 0) break;
        const hub = hubs[(s.ip ? s.ip.length : 0) % hubs.length]; // pseudo-random stable choice
        
        const interpolator = geoInterpolate([s.lon, s.lat], [hub.lon, hub.lat]);
        const lineCoords = [];
        for(let i=0; i<=1.0; i+=0.04) {
            lineCoords.push(interpolator(i));
        }
        
        let visible = false;
        for (const coord of lineCoords) {
           if (geoDistance([-this.rotY, -this.rotX], [coord[0], coord[1]]) <= Math.PI/2) { visible = true; break; }
        }
        
        if (visible) {
            ctx.beginPath();
            path({type: "LineString", coordinates: lineCoords});
            ctx.strokeStyle = 'rgba(0, 255, 255, 0.4)';
            ctx.lineWidth = 1.2;
            ctx.stroke();
            
            let packetT = (ts * 0.0003 + s.lon) % 1.0;
            if (packetT < 0) packetT += 1.0; // Fix JS negative modulo
            
            if (packetT > 0 && packetT < 1.0) {
               const packetPos = interpolator(packetT);
               if (geoDistance([-this.rotY, -this.rotX], [packetPos[0], packetPos[1]]) <= Math.PI/2) {
                   ctx.beginPath();
                   path.pointRadius(1.5);
                   path({type: "Point", coordinates: packetPos});
                   ctx.fillStyle = '#00ffff';
                   ctx.shadowBlur = 5;
                   ctx.shadowColor = '#00ffff';
                   ctx.fill();
                   ctx.shadowBlur = 0;
               }
            }
        }
    }
    ctx.globalAlpha = 1.0;

    // 9. Active Attack Vectors (True spherical Great Circles)
    if (this.status === 'warning' || this.status === 'thinking' || this.activity > 0) {
      const numAttacks = this.status === 'warning' ? 6 : 3;
      const sourceNodes = realNodes.length > 0 ? realNodes : this.nodes;
      
      for(let a=0; a<numAttacks; a++) {
        const cycleDuration = 1200 + a * 400;
        const rawT = (ts + a*900) % cycleDuration;
        const t = rawT / cycleDuration;
        
        const startNode = sourceNodes[(a * 37) % sourceNodes.length];
        const endNode = this.nodes[(a * 89 + 1) % this.nodes.length];
        
        const interpolator = geoInterpolate([startNode.lon, startNode.lat], [endNode.lon, endNode.lat]);
        const curPos = interpolator(t);
        
        const trailStart = Math.max(0, t - 0.15);
        const lineCoords = [];
        for(let i=trailStart; i<=t; i+=0.02) {
          lineCoords.push(interpolator(i));
        }
        lineCoords.push(curPos);
        
        ctx.beginPath();
        path({type: "LineString", coordinates: lineCoords});
        ctx.strokeStyle = 'rgba(255, 0, 60, 0.8)';
        ctx.lineWidth = 2.5;
        ctx.stroke();
        
        ctx.beginPath();
        path.pointRadius(3);
        path({type: "Point", coordinates: curPos});
        ctx.fillStyle = '#ff003c';
        ctx.shadowBlur = 12;
        ctx.shadowColor = '#ff003c';
        ctx.fill();
        ctx.shadowBlur = 0;

        if (t > 0.96) {
           this.impacts.push({ lat: endNode.lat, lon: endNode.lon, age: 0 });
        }
      }
    }

    // 10. Impact Ripples & WAF Shields
    for (let i = this.impacts.length - 1; i >= 0; i--) {
      const imp = this.impacts[i];
      imp.age += 0.03;
      if (imp.age > 1) { this.impacts.splice(i, 1); continue; }
      
      const p = projection([imp.lon, imp.lat]);
      if (p && geoDistance([-this.rotY, -this.rotX], [imp.lon, imp.lat]) <= Math.PI/2) {
          // Draw Shield Hexagon
          const size = 20 * Math.sin(imp.age * Math.PI);
          ctx.beginPath();
          for(let h=0; h<6; h++) {
              const angle = (h * Math.PI / 3) + ts * 0.002;
              const hx = p[0] + Math.cos(angle) * size;
              const hy = p[1] + Math.sin(angle) * size;
              if (h===0) ctx.moveTo(hx, hy);
              else ctx.lineTo(hx, hy);
          }
          ctx.closePath();
          ctx.strokeStyle = `rgba(0, 255, 255, ${1 - imp.age})`;
          ctx.fillStyle = `rgba(0, 255, 255, ${(1 - imp.age) * 0.1})`;
          ctx.lineWidth = 1.5;
          ctx.stroke();
          ctx.fill();
      }
      
      ctx.beginPath();
      path.pointRadius(imp.age * 40); 
      path({type: "Point", coordinates: [imp.lon, imp.lat]});
      ctx.strokeStyle = `rgba(255, 0, 60, ${(1 - imp.age) * 0.5})`;
      ctx.lineWidth = 2.5;
      ctx.stroke();
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    cancelAnimationFrame(this.raf);
  }
  
  render() { 
    return html`
      <canvas></canvas>
      
      <div class="threat-feed">
        <div class="feed-title">GLOBAL THREAT INTELLIGENCE</div>
        ${this.recentAttacks.map(a => html`
          <div class="feed-line" @click=${() => this._focusThreat(a)}>
             <div class="feed-main">
               <span class="time">[${a.time}]</span>
               <span class="source">[${a.source}]</span>
               <span class="method">${a.method}</span>
             </div>
             <div class="feed-details">
               <span class="attacker">${a.ip} (${a.country})</span>
               <span class="arrow">⟶</span>
               <span class="target">${a.targetCity}, ${a.targetCountry}</span>
             </div>
          </div>
        `)}
      </div>

      <div class="map-legend">
        <div class="legend-title">GLOBE LEGEND</div>
        <div class="legend-item"><div class="legend-color attacker"></div> Active Threats & Attackers</div>
        <div class="legend-item"><div class="legend-color botnet"></div> IoT Botnet Swarms</div>
        <div class="legend-item"><div class="legend-color tor"></div> Tor Exit Nodes</div>
        <div class="legend-item"><div class="legend-color server"></div> Public Servers & Nodes</div>
        <div class="legend-item"><div class="legend-color" style="background:rgba(255,150,0,1);box-shadow:0 0 8px rgba(255,150,0,1)"></div> Mobile Towers (Cellular)</div>
        <div class="legend-item"><div class="legend-color" style="background:rgba(50,150,255,1);box-shadow:0 0 8px rgba(50,150,255,1)"></div> Datacenters</div>
        <div class="legend-item"><div class="legend-color" style="background:rgba(255,0,150,1);box-shadow:0 0 8px rgba(255,0,150,1)"></div> IXPs (Internet Exchange)</div>
        <div class="legend-item"><div class="legend-color hub"></div> Central Infrastructure Hubs</div>
        <div class="legend-item"><div class="legend-line attack-line"></div> Attack Vectors</div>
        <div class="legend-item"><div class="legend-line data-line"></div> Sat-Relays & Data Routes</div>
        <div class="legend-item"><div class="legend-line cable"></div> Undersea Backbones</div>
        <div class="legend-item"><div class="legend-color shield"></div> WAF Defensive Shields</div>
      </div>

      ${this.selectedNode ? html`
        <div class="osint-panel">
          <div class="panel-header">TARGET LOCKED // OSINT PROFILE</div>
          <div class="osint-body">
            <div class="stat"><span class="lbl">IP_ADDR</span> <span class="val red">${this.selectedNode.ip}</span></div>
            <div class="stat"><span class="lbl">LAT_LON</span> <span class="val">${this.selectedNode.lat.toFixed(4)}, ${this.selectedNode.lon.toFixed(4)}</span></div>
            
            ${this.osintLoading ? html`
               <div class="stat"><span class="lbl">OSINT_DB</span> <span class="val" style="color:#00ffff; animation: blink 1s infinite;">Querying Global Registries...</span></div>
            ` : this.osintData ? html`
               <div class="stat"><span class="lbl">REG_NAME</span> <span class="val">${this.osintData.name || "UNREGISTERED"}</span></div>
               ${this.osintData.entities?.length > 0 ? html`
                 <div class="stat"><span class="lbl">ORG_ISP</span> <span class="val">${this.osintData.entities[0].name || this.selectedNode.org || "Unknown"}</span></div>
                 ${this.osintData.entities[0].email ? html`<div class="stat"><span class="lbl">ABUSE_EMAIL</span> <span class="val" style="color:#ffcc00">${this.osintData.entities[0].email}</span></div>` : null}
                 ${this.osintData.entities[0].phone ? html`<div class="stat"><span class="lbl">PHONE</span> <span class="val">${this.osintData.entities[0].phone}</span></div>` : null}
               ` : html`
                 <div class="stat"><span class="lbl">ORG_ISP</span> <span class="val">${this.selectedNode.org || "Unknown"}</span></div>
               `}
            ` : html`
               <div class="stat"><span class="lbl">ORG_ISP</span> <span class="val">${this.selectedNode.org || "Unknown"}</span></div>
            `}
            
            <div class="stat"><span class="lbl">THREAT_SRC</span> <span class="val" style="color:#ffcc00">${this.selectedNode.source || "SANS ISC"}</span></div>
            <div class="stat"><span class="lbl">THREAT_LVL</span> <span class="val red">CRITICAL (ACTIVE)</span></div>
            
            <div class="actions">
              <button class="btn" @click=${() => { this.targetRot = null; this.selectedNode = null; }}>DISENGAGE</button>
            </div>
          </div>
        </div>
      ` : null}
    `; 
  }
}

declare global {
  interface HTMLElementTagNameMap { "threat-globe": ThreatGlobe; }
}
