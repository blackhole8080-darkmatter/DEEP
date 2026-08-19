import{i as b,b as r,A as c,a as v,r as h,t as f}from"./index-CBQjtX3d.js";var y=Object.defineProperty,$=Object.getOwnPropertyDescriptor,p=(t,i,l,a)=>{for(var s=a>1?void 0:a?$(i,l):i,o=t.length-1,d;o>=0;o--)(d=t[o])&&(s=(a?d(i,l,s):d(s))||s);return a&&s&&y(i,l,s),s};const x=300*1e3;let n=class extends b{constructor(){super(...arguments),this.stats=null,this.error="",this.loading=!0,this.timer=0}connectedCallback(){super.connectedCallback(),this.load(),this.timer=window.setInterval(()=>void this.load(),x)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.timer)}async load(){try{const t=await fetch("/api/intel/stats");if(!t.ok)throw new Error(`HTTP ${t.status}`);this.stats=await t.json(),this.error=""}catch(t){this.error=t.message}finally{this.loading=!1}}tile(t,i,l=""){const a=t==null;return r`
      <div class="tile ${a?"muted":l}">
        <div class="value">${a?"unavailable":t}</div>
        <div class="label">${i}</div>
      </div>
    `}render(){var d,g,m,u;if(this.loading)return r`<div class="state">Loading global intelligence…</div>`;if(!this.stats)return r`<div class="state">Could not reach the intel layer: ${this.error}</div>`;const{kev:t,botnet:i,anonymity:l,sources:a,degraded:s}=this.stats,o=Object.keys(s??{});return r`
      ${o.length?r`
            <div class="banner">
              <strong>${o.length} source(s) degraded</strong> — figures below
              are computed only from feeds that answered.
              <ul>
                ${o.map(e=>r`<li>${e}: ${s[e]}</li>`)}
              </ul>
            </div>
          `:c}

      <h3>Actively exploited (CISA KEV)</h3>
      <div class="tiles">
        ${this.tile(t.total,"catalog entries")}
        ${this.tile(t.added_7d,"added, last 7 days",(t.added_7d??0)>5?"warn":"")}
        ${this.tile(t.added_30d,"added, last 30 days")}
        ${this.tile(t.remediation_overdue,"remediation overdue","alert")}
        ${this.tile(t.remediation_due_14d,"due within 14 days","warn")}
        ${this.tile(t.ransomware_linked,"ransomware-linked","alert")}
      </div>

      ${t.available&&((d=t.latest)!=null&&d.length)?r`
            <h3>Newest KEV entries</h3>
            <div class="scroll-x">
              <table>
                <thead>
                  <tr><th>CVE</th><th>Vendor</th><th>Product</th><th>Added</th><th>Remediate by</th><th></th></tr>
                </thead>
                <tbody>
                  ${t.latest.slice(0,12).map(e=>r`
                      <tr>
                        <td class="mono">${e.cve}</td>
                        <td>${e.vendor}</td>
                        <td>${e.product}</td>
                        <td class="mono">${e.added}</td>
                        <td class="mono">${e.due}</td>
                        <td>${e.ransomware?r`<span class="pill ransom">ransomware</span>`:c}</td>
                      </tr>
                    `)}
                </tbody>
              </table>
            </div>
          `:c}

      <h3>Botnet infrastructure &amp; anonymity</h3>
      <div class="tiles">
        ${this.tile(i.active_c2_servers,"active C2 servers","alert")}
        ${this.tile(l.tor_exit_nodes,"Tor exit nodes")}
        ${this.tile((m=(g=i.families)==null?void 0:g[0])==null?void 0:m.family,"top malware family")}
      </div>
      ${i.available&&((u=i.families)!=null&&u.length)?r`
            <p class="note">
              Families:
              ${i.families.slice(0,6).map(e=>`${e.family} (${e.count})`).join(", ")}
            </p>
          `:c}

      <h3>Source health</h3>
      <div class="tiles">
        ${this.tile(`${a.available_now}/${a.total}`,"sources available")}
        ${this.tile(a.keyless,"keyless (no signup)")}
        ${this.tile(`${a.key_configured}/${a.key_required}`,"keyed sources configured")}
      </div>
      <div class="scroll-x">
        <table>
          <thead><tr><th>Source</th><th>Category</th><th>Status</th><th>Docs</th></tr></thead>
          <tbody>
            ${a.sources.map(e=>r`
                <tr>
                  <td>${e.name}</td>
                  <td>${e.category}</td>
                  <td>
                    ${e.configured?r`<span class="pill live">live</span>`:r`<span class="pill gated">set ${e.env_var}</span>`}
                  </td>
                  <td><a href=${e.docs_url} target="_blank" rel="noreferrer noopener">docs</a></td>
                </tr>
              `)}
          </tbody>
        </table>
      </div>

      <p class="note">Generated ${new Date(this.stats.generated_at).toLocaleString()} · refreshes every 5 minutes.</p>
    `}};n.styles=v`
    :host { display: block; height: 100%; overflow-y: auto; padding: 4px 2px 20px; }

    h3 {
      margin: 22px 0 10px;
      font-size: 0.7rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      opacity: 0.55;
      font-weight: 600;
    }
    h3:first-of-type { margin-top: 6px; }

    .tiles {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
    }
    .tile {
      border: 1px solid rgba(120, 200, 230, 0.16);
      border-radius: 8px;
      background: rgba(120, 200, 230, 0.045);
      padding: 12px 14px;
    }
    .tile .value {
      font-size: 1.6rem;
      font-variant-numeric: tabular-nums;
      line-height: 1.1;
      font-family: var(--ds-font-mono, monospace);
    }
    .tile .label {
      margin-top: 5px;
      font-size: 0.68rem;
      opacity: 0.62;
      letter-spacing: 0.04em;
    }
    .tile.alert { border-color: rgba(255, 140, 140, 0.4); background: rgba(255, 120, 120, 0.07); }
    .tile.alert .value { color: rgba(255, 165, 165, 0.95); }
    .tile.warn { border-color: rgba(255, 210, 130, 0.35); }
    .tile.warn .value { color: rgba(255, 215, 150, 0.95); }
    .tile.muted .value { opacity: 0.35; font-size: 1rem; }

    table { width: 100%; border-collapse: collapse; font-size: 0.74rem; }
    th, td {
      text-align: left;
      padding: 5px 8px;
      border-bottom: 1px solid rgba(120, 200, 230, 0.09);
      vertical-align: top;
    }
    th { opacity: 0.5; font-weight: 500; text-transform: uppercase; font-size: 0.63rem; letter-spacing: 0.08em; }
    td.mono { font-family: var(--ds-font-mono, monospace); white-space: nowrap; }
    .scroll-x { overflow-x: auto; }

    .pill {
      display: inline-block;
      border-radius: 3px;
      padding: 1px 6px;
      font-size: 0.62rem;
      letter-spacing: 0.04em;
    }
    .pill.live { background: rgba(120, 240, 180, 0.16); color: rgba(160, 250, 200, 0.95); }
    .pill.gated { background: rgba(255, 210, 130, 0.14); color: rgba(255, 220, 160, 0.9); }
    .pill.ransom { background: rgba(255, 130, 130, 0.16); color: rgba(255, 170, 170, 0.95); }

    .note { font-size: 0.72rem; opacity: 0.55; margin: 8px 0 0; }
    .banner {
      border: 1px solid rgba(255, 180, 120, 0.35);
      background: rgba(255, 170, 110, 0.07);
      border-radius: 6px;
      padding: 9px 12px;
      font-size: 0.73rem;
      margin-bottom: 4px;
    }
    .banner ul { margin: 6px 0 0; padding-left: 18px; }
    .state { padding: 24px; opacity: 0.6; font-size: 0.8rem; }
    a { color: rgba(150, 210, 255, 0.85); }
  `;p([h()],n.prototype,"stats",2);p([h()],n.prototype,"error",2);p([h()],n.prototype,"loading",2);n=p([f("intel-stats-view")],n);export{n as IntelStatsView};
//# sourceMappingURL=intel-stats-view-DTfwczI2.js.map
