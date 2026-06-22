import{e as b,n as p,i as c,d as n,t as v}from"./index-BZpHEIVQ.js";var u=Object.defineProperty,h=Object.getOwnPropertyDescriptor,i=(l,s,t,a)=>{for(var r=a>1?void 0:a?h(s,t):s,o=l.length-1,d;o>=0;o--)(d=l[o])&&(r=(a?d(s,t,r):d(r))||r);return a&&r&&u(s,t,r),r};let e=class extends c{constructor(){super(...arguments),this.heading="",this.variant="solid"}render(){return n`
      <section class=${this.variant}>
        ${this.heading?n`<header><span>${this.heading}</span><slot name="actions"></slot></header>`:""}
        <div class="body"><slot></slot></div>
      </section>
    `}};e.styles=b`
    :host { display: block; }
    section {
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      box-shadow: var(--ds-elev-2);
      overflow: hidden;
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
    }
    /* Default panels are now lightly translucent so the living-brain background
       shows through — deeper fill + small blur keeps text readable (no heavy
       blur here; that's reserved for sidebar/topbar to keep compositing cheap). */
    .solid {
      background: var(--ds-glass-deep);
      -webkit-backdrop-filter: blur(var(--ds-blur-sm));
      backdrop-filter: blur(var(--ds-blur-sm));
      border-color: var(--ds-border-glass);
    }
    .glass {
      background: var(--ds-glass-light);
      -webkit-backdrop-filter: blur(var(--ds-blur-md));
      backdrop-filter: blur(var(--ds-blur-md));
      border-color: var(--ds-border-glass);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--ds-space-3) var(--ds-space-4);
      border-bottom: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
      font-weight: 600;
      letter-spacing: var(--ds-tracking-wide);
      color: var(--ds-text-soft);
      text-transform: uppercase;
    }
    .body { padding: var(--ds-space-4); }
    @keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
    @media (prefers-reduced-motion: reduce) { section { animation: none; } }
  `;i([p()],e.prototype,"heading",2);i([p()],e.prototype,"variant",2);e=i([v("ds-panel")],e);
//# sourceMappingURL=ds-panel-B0Coku7q.js.map
