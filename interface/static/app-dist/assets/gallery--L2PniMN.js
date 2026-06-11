import{i as v,n as p,e as f,a as b,b as i,t as h,c as u}from"./index-C1qtzXJ3.js";import"./ds-panel-DApGqLE2.js";var g=Object.defineProperty,y=Object.getOwnPropertyDescriptor,o=(e,a,n,r)=>{for(var s=r>1?void 0:r?y(a,n):a,d=e.length-1,l;d>=0;d--)(l=e[d])&&(s=(r?l(a,n,s):l(s))||s);return r&&s&&g(a,n,s),s};let t=class extends b{constructor(){super(...arguments),this.label="",this.placeholder="",this.value="",this.type="text"}onInput(){this.value=this.input.value,this.dispatchEvent(new CustomEvent("ds-input",{detail:this.value,bubbles:!0,composed:!0}))}onKeydown(e){e.key==="Enter"&&this.dispatchEvent(new CustomEvent("ds-submit",{detail:this.value,bubbles:!0,composed:!0}))}render(){return i`
      ${this.label?i`<label>${this.label}</label>`:""}
      <input
        .type=${this.type}
        .value=${this.value}
        placeholder=${this.placeholder}
        @input=${this.onInput}
        @keydown=${this.onKeydown}
      />
    `}};t.styles=v`
    :host { display: block; }
    label {
      display: block;
      margin-bottom: var(--ds-space-1);
      font-size: var(--ds-text-xs);
      letter-spacing: var(--ds-tracking-wide);
      text-transform: uppercase;
      color: var(--ds-text-muted);
    }
    input {
      width: 100%;
      padding: var(--ds-space-2) var(--ds-space-3);
      font-family: var(--ds-font-sans);
      font-size: var(--ds-text-sm);
      color: var(--ds-text);
      background: var(--ds-surface-2);
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-sm);
      transition: border-color var(--ds-dur-fast) var(--ds-ease-out);
    }
    input::placeholder { color: var(--ds-text-faint); }
    input:hover { border-color: var(--ds-border-strong); }
    input:focus { outline: none; border-color: var(--ds-border-accent); box-shadow: var(--ds-focus-ring); }
  `;o([p()],t.prototype,"label",2);o([p()],t.prototype,"placeholder",2);o([p()],t.prototype,"value",2);o([p()],t.prototype,"type",2);o([f("input")],t.prototype,"input",2);t=o([h("ds-field")],t);var m=Object.getOwnPropertyDescriptor,x=(e,a,n,r)=>{for(var s=r>1?void 0:r?m(a,n):a,d=e.length-1,l;d>=0;d--)(l=e[d])&&(s=l(s)||s);return s};let c=class extends b{render(){return i`
      <h1>Design system gallery</h1>

      <ds-panel heading="Buttons">
        <div class="row">
          <ds-button variant="primary">Primary</ds-button>
          <ds-button>Ghost</ds-button>
          <ds-button variant="danger">Danger</ds-button>
          <ds-button variant="primary" size="sm">Small</ds-button>
          <ds-button disabled>Disabled</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Fields">
        <div class="row" style="align-items:end">
          <ds-field label="Name" placeholder="Type something…" style="flex:1"></ds-field>
          <ds-field label="Token" placeholder="••••" type="password" style="flex:1"></ds-field>
        </div>
      </ds-panel>

      <ds-panel heading="Toasts">
        <div class="row">
          <ds-button @click=${()=>u("Saved successfully","success")}>Success</ds-button>
          <ds-button @click=${()=>u("Heads up — informational","info")}>Info</ds-button>
          <ds-button variant="danger" @click=${()=>u("Something failed","danger")}>Danger</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Surfaces" variant="glass">
        <p style="margin:0;color:var(--ds-text-soft)">This panel uses the glass variant.</p>
      </ds-panel>

      <ds-panel heading="Color tokens">
        <div class="swatches">
          ${["--ds-bg","--ds-surface-1","--ds-surface-2","--ds-surface-3","--ds-accent","--ds-success","--ds-warning","--ds-danger","--ds-info"].map(e=>i`<div class="sw" style="background: var(${e})">${e.slice(5)}</div>`)}
        </div>
      </ds-panel>
    `}};c.styles=v`
    :host {
      display: grid;
      gap: var(--ds-space-5);
      padding: var(--ds-space-6);
      max-width: 860px;
      margin: 0 auto;
    }
    .row { display: flex; gap: var(--ds-space-3); align-items: center; flex-wrap: wrap; }
    h1 { font-size: var(--ds-text-xl); margin: 0; }
    .swatches { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; }
    .sw {
      width: 72px; height: 48px;
      border-radius: var(--ds-radius-sm);
      border: 1px solid var(--ds-border);
      display: grid; place-items: end start;
      padding: 4px; font-size: 9px; color: var(--ds-text-muted);
      font-family: var(--ds-font-mono);
    }
  `;c=x([h("ds-gallery")],c);export{c as DsGallery};
//# sourceMappingURL=gallery--L2PniMN.js.map
