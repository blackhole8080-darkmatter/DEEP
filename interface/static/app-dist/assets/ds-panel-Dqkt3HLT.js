import{i as c,n as p,a as v,b as l,t as b}from"./index-TJd2YPHQ.js";var f=Object.defineProperty,u=Object.getOwnPropertyDescriptor,i=(n,s,t,a)=>{for(var r=a>1?void 0:a?u(s,t):s,o=n.length-1,d;o>=0;o--)(d=n[o])&&(r=(a?d(s,t,r):d(r))||r);return a&&r&&f(s,t,r),r};let e=class extends v{constructor(){super(...arguments),this.heading="",this.variant="solid"}render(){return l`
      <section class=${this.variant}>
        ${this.heading?l`<header><span>${this.heading}</span><slot name="actions"></slot></header>`:""}
        <div class="body"><slot></slot></div>
      </section>
    `}};e.styles=c`
    :host { display: block; }
    section {
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      box-shadow: var(--ds-elev-2);
      overflow: hidden;
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
    }
    .solid { background: var(--ds-surface-1); }
    .glass {
      background: var(--ds-glass);
      -webkit-backdrop-filter: blur(var(--ds-blur-md));
      backdrop-filter: blur(var(--ds-blur-md));
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
  `;i([p()],e.prototype,"heading",2);i([p()],e.prototype,"variant",2);e=i([b("ds-panel")],e);
//# sourceMappingURL=ds-panel-Dqkt3HLT.js.map
