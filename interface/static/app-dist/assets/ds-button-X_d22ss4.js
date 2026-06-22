import{e as c,n as i,i as b,d as v,t as u}from"./index-BZpHEIVQ.js";var p=Object.defineProperty,f=Object.getOwnPropertyDescriptor,o=(l,a,e,t)=>{for(var r=t>1?void 0:t?f(a,e):a,d=l.length-1,n;d>=0;d--)(n=l[d])&&(r=(t?n(a,e,r):n(r))||r);return t&&r&&p(a,e,r),r};let s=class extends b{constructor(){super(...arguments),this.variant="ghost",this.size="md",this.disabled=!1}render(){return v`
      <button class="${this.variant} ${this.size}" ?disabled=${this.disabled}>
        <slot></slot>
      </button>
    `}};s.styles=c`
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
  `;o([i()],s.prototype,"variant",2);o([i()],s.prototype,"size",2);o([i({type:Boolean})],s.prototype,"disabled",2);s=o([u("ds-button")],s);
//# sourceMappingURL=ds-button-X_d22ss4.js.map
