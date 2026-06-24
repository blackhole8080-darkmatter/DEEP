import{i as p,f as m,a as g,b,c as f,d as e,e as u,r as l,t as v}from"./index-C-DdVA2t.js";import{o as h,r as x,k as y}from"./math-B29P3NG3.js";import"./ds-panel-B3ARb1Qv.js";var w=Object.defineProperty,$=Object.getOwnPropertyDescriptor,n=(t,a,i,r)=>{for(var s=r>1?void 0:r?$(a,i):a,d=t.length-1,c;d>=0;d--)(c=t[d])&&(s=(r?c(a,i,s):c(s))||s);return r&&s&&w(a,i,s),s};function _(t){const a=t.atomic_number;return a>=57&&a<=71?{row:9,col:3+(a-57)}:a>=89&&a<=103?{row:10,col:3+(a-89)}:t.group&&t.period?{row:t.period,col:t.group}:null}let o=class extends p{constructor(){super(...arguments),this.elements=[],this.detail=null,this.constants=[],this.formulas=[]}connectedCallback(){super.connectedCallback(),m().then(t=>this.elements=t.elements).catch(()=>{}),g().then(t=>this.constants=t.constants).catch(()=>{}),b().then(t=>this.formulas=t.formulas).catch(()=>{})}async pick(t){const a=await f(t).catch(()=>null);a!=null&&a.ok&&a.element&&(this.detail=a.element)}renderDetail(){const t=this.detail;if(!t)return e`<span style="color:var(--ds-text-muted)">Select an element for verified data.</span>`;const a=(i,r)=>r==null?"":e`<div class="row"><span>${i}</span><b>${r}</b></div>`;return e`
      <div class="detail">
        <span class="title">${t.name} (${t.symbol}) · Z=${t.atomic_number}</span>
        ${a("Atomic weight",t.atomic_weight)}
        ${a("Electron config",t.electron_configuration)}
        ${a("Electronegativity",t.electronegativity)}
        ${a("Oxidation states",Array.isArray(t.oxidation_states)?t.oxidation_states.join(", "):null)}
        ${a("Melting point (K)",t.melting_point_K)}
        ${a("Boiling point (K)",t.boiling_point_K)}
        ${a("Density (g/cm³)",t.density_g_cm3)}
        ${a("Category",t.series)}
        ${a("Discovered",t.discovery_year)}
      </div>
    `}render(){return e`
      <ds-panel heading="Periodic table · ${this.elements.length} elements · curated data">
        <div class="grid">
          ${this.elements.map(t=>{const a=_(t);return a?e`
              <button class="cell cat-${t.category}" title=${t.name}
                style="grid-row:${a.row};grid-column:${a.col}"
                @click=${()=>void this.pick(t.atomic_number)}>
                <span class="z">${t.atomic_number}</span>
                <span class="sym">${t.symbol}</span>
              </button>
            `:""})}
        </div>
        <div style="margin-top:var(--ds-space-4)">${this.renderDetail()}</div>
      </ds-panel>

      <div class="cols">
        <ds-panel heading="Physical constants · CODATA">
          <div class="list mono">
            ${this.constants.map(t=>e`<div class="row"><span>${t.name} (${t.symbol})</span><b>${t.value} ${t.unit}</b></div>`)}
          </div>
        </ds-panel>
        <ds-panel heading="Formula library · ancient → modern">
          <div class="list">
            ${this.formulas.map(t=>e`<div class="frow">
                <span class="fname">${t.name} <span class="era">${t.era}</span></span>
                ${t.latex?e`<div class="ftex">${h(x(t.latex,!0))}</div>`:e`<b class="mono">${t.formula}</b>`}
              </div>`)}
          </div>
        </ds-panel>
      </div>
    `}};o.styles=[y,u`
    :host {
      display: grid;
      gap: var(--ds-space-5);
      padding: var(--ds-space-5);
      max-width: 1100px;
      margin: 0 auto;
    }
    .grid { display: grid; grid-template-columns: repeat(18, 1fr); gap: 3px; }
    button.cell {
      aspect-ratio: 1; min-width: 0; padding: 2px 3px;
      display: flex; flex-direction: column; align-items: flex-start; justify-content: space-between;
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-xs);
      background: var(--ds-surface-2);
      color: var(--ds-text); cursor: pointer; overflow: hidden;
      transition: transform var(--ds-dur-fast) var(--ds-ease-spring), box-shadow var(--ds-dur-fast) var(--ds-ease-out);
    }
    button.cell:hover { transform: scale(1.14); box-shadow: var(--ds-elev-3); z-index: 2; }
    .z { font-size: 0.5rem; opacity: 0.65; }
    .sym { font-size: 0.85rem; font-weight: 700; line-height: 1; }
    .cat-nonmetal { background: rgba(86,197,150,0.16); border-color: rgba(86,197,150,0.45); }
    .cat-noble { background: rgba(181,140,255,0.16); border-color: rgba(181,140,255,0.45); }
    .cat-alkali { background: rgba(229,115,106,0.16); border-color: rgba(229,115,106,0.45); }
    .cat-alkaline { background: rgba(224,163,90,0.16); border-color: rgba(224,163,90,0.45); }
    .cat-metalloid { background: rgba(94,200,229,0.16); border-color: rgba(94,200,229,0.45); }
    .cat-halogen { background: rgba(124,147,255,0.16); border-color: rgba(124,147,255,0.45); }
    .cat-transition { background: rgba(154,140,255,0.12); border-color: rgba(154,140,255,0.35); }
    .cat-lanthanide { background: rgba(94,200,229,0.10); border-color: rgba(94,200,229,0.3); }
    .cat-actinide { background: rgba(86,197,150,0.10); border-color: rgba(86,197,150,0.3); }
    .detail { font-size: var(--ds-text-sm); display: grid; gap: 4px; }
    .detail .title { font-size: var(--ds-text-lg); font-weight: 700; color: var(--ds-accent); }
    .row { display: flex; justify-content: space-between; gap: var(--ds-space-4); border-bottom: 1px solid var(--ds-border); padding: 2px 0; }
    .row span { color: var(--ds-text-soft); }
    .row b { font-family: var(--ds-font-mono); font-weight: 500; }
    .cols { display: grid; grid-template-columns: 1fr 1fr; gap: var(--ds-space-5); }
    @media (max-width: 800px) { .cols { grid-template-columns: 1fr; } }
    .mono { font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); }
    .list { display: grid; gap: 4px; max-height: 300px; overflow-y: auto; }
    .era { color: var(--ds-text-faint); text-transform: uppercase; font-size: 0.6rem; letter-spacing: var(--ds-tracking-wide); }
    .frow { display: grid; gap: 2px; border-bottom: 1px solid var(--ds-border); padding: 6px 0; }
    .frow .fname { font-size: var(--ds-text-xs); color: var(--ds-text-soft); }
    .frow .ftex { overflow-x: auto; }
    .frow .ftex .katex { color: var(--ds-text); font-size: 1.05em; }
  `];n([l()],o.prototype,"elements",2);n([l()],o.prototype,"detail",2);n([l()],o.prototype,"constants",2);n([l()],o.prototype,"formulas",2);o=n([v("science-view")],o);export{o as ScienceView};
//# sourceMappingURL=science-view-DccJByCK.js.map
