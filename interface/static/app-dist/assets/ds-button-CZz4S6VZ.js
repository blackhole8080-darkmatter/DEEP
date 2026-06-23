import{e as c,n as i,i as l,d as v,t as g}from"./index-DZt9GVll.js";var u=Object.defineProperty,p=Object.getOwnPropertyDescriptor,t=(b,s,e,o)=>{for(var r=o>1?void 0:o?p(s,e):s,d=b.length-1,n;d>=0;d--)(n=b[d])&&(r=(o?n(s,e,r):n(r))||r);return o&&r&&u(s,e,r),r};let a=class extends l{constructor(){super(...arguments),this.variant="ghost",this.size="md",this.disabled=!1}render(){return v`
      <button class="${this.variant} ${this.size}" ?disabled=${this.disabled}>
        <slot></slot>
      </button>
    `}};a.styles=c`
    :host { display: inline-block; }
    button {
      display: inline-flex;
      align-items: center;
      gap: var(--ds-space-2);
      font-family: var(--ds-font-sans);
      font-weight: 500;
      border-radius: var(--ds-radius-sm);
      border: 1px solid var(--ds-border);
      background: var(--ds-surface-2);
      color: var(--ds-text);
      cursor: pointer;
      transition:
        background var(--ds-dur-fast) var(--ds-ease-out),
        border-color var(--ds-dur-fast) var(--ds-ease-out),
        transform var(--ds-dur-fast) var(--ds-ease-spring);
    }
    button:hover:not(:disabled) { background: var(--ds-surface-3); transform: translateY(-1px); }
    button:active:not(:disabled) { transform: translateY(0); }
    button:disabled { opacity: 0.45; cursor: not-allowed; }
    button:focus-visible { outline: none; box-shadow: var(--ds-focus-ring); }

    .md { padding: var(--ds-space-2) var(--ds-space-4); font-size: var(--ds-text-sm); }
    .sm { padding: var(--ds-space-1) var(--ds-space-3); font-size: var(--ds-text-xs); }

    .primary {
      background: var(--ds-accent);
      border-color: var(--ds-accent);
      color: var(--ds-on-accent);
      font-weight: 600;
    }
    .primary:hover:not(:disabled) { background: var(--ds-accent); filter: brightness(1.1); box-shadow: var(--ds-glow); }
    .danger { border-color: rgba(229, 115, 106, 0.4); color: var(--ds-danger); background: rgba(229, 115, 106, 0.08); }
    .danger:hover:not(:disabled) { background: rgba(229, 115, 106, 0.16); }

    /* ETIS overrides */
    :host-context([data-skin="etis"]) .primary {
      background: rgba(var(--ds-periwinkle-rgb), 0.08);
      border-color: var(--ds-accent);
      color: var(--ds-accent);
    }
    :host-context([data-skin="etis"]) .primary:hover:not(:disabled) {
      background: rgba(var(--ds-periwinkle-rgb), 0.15);
      box-shadow: var(--ds-glow);
    }
    :host-context([data-skin="etis"]) .danger {
      border-color: var(--ds-danger);
      color: var(--ds-danger);
      background: rgba(255, 68, 102, 0.08);
    }
    :host-context([data-skin="etis"]) .danger:hover:not(:disabled) {
      background: rgba(255, 68, 102, 0.16);
      box-shadow: 0 0 12px rgba(255, 68, 102, 0.2);
    }
  `;t([i()],a.prototype,"variant",2);t([i()],a.prototype,"size",2);t([i({type:Boolean})],a.prototype,"disabled",2);a=t([g("ds-button")],a);
//# sourceMappingURL=ds-button-CZz4S6VZ.js.map
