import{a as p,f as g,d as m,g as b,h as u,b as s,i as v,r as l,t as f}from"./index-CUIHgJB1.js";import"./ds-panel-Dgug3kt1.js";var h=Object.defineProperty,y=Object.getOwnPropertyDescriptor,n=(a,t,i,e)=>{for(var r=e>1?void 0:e?y(t,i):t,d=a.length-1,c;d>=0;d--)(c=a[d])&&(r=(e?c(t,i,r):c(r))||r);return e&&r&&h(t,i,r),r};function x(a){const t=a.atomic_number;return t>=57&&t<=71?{row:9,col:3+(t-57)}:t>=89&&t<=103?{row:10,col:3+(t-89)}:a.group&&a.period?{row:a.period,col:a.group}:null}let o=class extends p{constructor(){super(...arguments),this.elements=[],this.detail=null,this.constants=[],this.formulas=[]}connectedCallback(){super.connectedCallback(),g().then(a=>this.elements=a.elements).catch(()=>{}),m().then(a=>this.constants=a.constants).catch(()=>{}),b().then(a=>this.formulas=a.formulas).catch(()=>{})}async pick(a){const t=await u(a).catch(()=>null);t!=null&&t.ok&&t.element&&(this.detail=t.element)}renderDetail(){const a=this.detail;if(!a)return s`<span style="color:var(--ds-text-muted)">Select an element for verified data.</span>`;const t=(i,e)=>e==null?"":s`<div class="row"><span>${i}</span><b>${e}</b></div>`;return s`
      <div class="detail">
        <span class="title">${a.name} (${a.symbol}) · Z=${a.atomic_number}</span>
        ${t("Atomic weight",a.atomic_weight)}
        ${t("Electron config",a.electron_configuration)}
        ${t("Electronegativity",a.electronegativity)}
        ${t("Oxidation states",Array.isArray(a.oxidation_states)?a.oxidation_states.join(", "):null)}
        ${t("Melting point (K)",a.melting_point_K)}
        ${t("Boiling point (K)",a.boiling_point_K)}
        ${t("Density (g/cm³)",a.density_g_cm3)}
        ${t("Category",a.series)}
        ${t("Discovered",a.discovery_year)}
      </div>
    `}render(){return s`
      <ds-panel heading="Periodic table · ${this.elements.length} elements · curated data">
        <div class="grid">
          ${this.elements.map(a=>{const t=x(a);return t?s`
              <button class="cell cat-${a.category}" title=${a.name}
                style="grid-row:${t.row};grid-column:${t.col}"
                @click=${()=>void this.pick(a.atomic_number)}>
                <span class="z">${a.atomic_number}</span>
                <span class="sym">${a.symbol}</span>
              </button>
            `:""})}
        </div>
        <div style="margin-top:var(--ds-space-4)">${this.renderDetail()}</div>
      </ds-panel>

      <div class="cols">
        <ds-panel heading="Physical constants · CODATA">
          <div class="list mono">
            ${this.constants.map(a=>s`<div class="row"><span>${a.name} (${a.symbol})</span><b>${a.value} ${a.unit}</b></div>`)}
          </div>
        </ds-panel>
        <ds-panel heading="Formula library · ancient → modern">
          <div class="list mono">
            ${this.formulas.map(a=>s`<div class="row"><span>${a.name} <span class="era">${a.era}</span></span><b>${a.formula}</b></div>`)}
          </div>
        </ds-panel>
      </div>
    `}};o.styles=v`
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
  `;n([l()],o.prototype,"elements",2);n([l()],o.prototype,"detail",2);n([l()],o.prototype,"constants",2);n([l()],o.prototype,"formulas",2);o=n([f("science-view")],o);export{o as ScienceView};
//# sourceMappingURL=science-view-x5XOaZK2.js.map
