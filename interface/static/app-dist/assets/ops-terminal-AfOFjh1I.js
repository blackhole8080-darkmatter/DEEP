import{i as u,A as c,b as a,a as f,r as l,e as d,t as m}from"./index-2Z09ZJ8J.js";var g=Object.defineProperty,y=Object.getOwnPropertyDescriptor,n=(t,s,o,i)=>{for(var e=i>1?void 0:i?y(s,o):s,p=t.length-1,h;p>=0;p--)(h=t[p])&&(e=(i?h(s,o,e):h(e))||e);return i&&e&&g(s,o,e),e};const b=`DEEP OPERATIONS TERMINAL
Read-only intelligence console. 'help' lists commands, Tab completes, ↑/↓ recalls.`;let r=class extends u{constructor(){super(...arguments),this.lines=[{kind:"system",text:b}],this.draft="",this.busy=!1,this.commands=[],this.suggestions=[],this.history=[],this.historyIndex=-1}connectedCallback(){super.connectedCallback(),this.loadCommands()}async loadCommands(){try{const t=await fetch("/api/intel/terminal/commands");if(!t.ok)throw new Error(`${t.status}`);const s=await t.json();this.commands=s.commands??[]}catch{this.pushLine({kind:"error",text:"Could not load the command catalog. Tab completion is unavailable; commands still run."})}}pushLine(t){this.lines=[...this.lines,t],this.updateComplete.then(()=>{this.scroller&&(this.scroller.scrollTop=this.scroller.scrollHeight)})}async run(t){var o;const s=t.trim();if(s){if(this.pushLine({kind:"input",text:s}),this.history=[s,...this.history.filter(i=>i!==s)].slice(0,100),this.historyIndex=-1,this.draft="",this.suggestions=[],s==="clear"){this.lines=[];return}this.busy=!0;try{const i=await fetch("/api/intel/terminal/exec",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({line:s})});if(!i.ok){this.pushLine({kind:"error",text:`Request failed: HTTP ${i.status}`});return}const e=await i.json();if(((o=e.data)==null?void 0:o.action)==="clear"){this.lines=[];return}if(!e.ok){this.pushLine({kind:"error",text:e.error||"command failed"}),e.text&&this.pushLine({kind:"output",text:e.text});return}this.pushLine({kind:"output",text:e.text||"(no output)",elapsed:e.elapsed_ms})}catch(i){this.pushLine({kind:"error",text:`Network error: ${i.message}`})}finally{this.busy=!1,this.updateComplete.then(()=>{var i;return(i=this.input)==null?void 0:i.focus()})}}}onInput(t){this.draft=t.target.value;const s=this.draft.trimStart();this.suggestions=s&&!s.includes(" ")?this.commands.filter(o=>o.name.startsWith(s.toLowerCase())).slice(0,8):[]}onKey(t){if(t.key==="Enter"){t.preventDefault(),this.busy||this.run(this.draft);return}if(t.key==="Tab"){t.preventDefault();const[s]=this.suggestions;s&&(this.draft=`${s.name} `,this.suggestions=[]);return}if(t.key==="ArrowUp"){t.preventDefault(),this.historyIndex+1<this.history.length&&(this.historyIndex+=1,this.draft=this.history[this.historyIndex]);return}t.key==="ArrowDown"&&(t.preventDefault(),this.historyIndex>0?(this.historyIndex-=1,this.draft=this.history[this.historyIndex]):(this.historyIndex=-1,this.draft=""))}render(){return a`
      <div class="wrap" @click=${()=>{var t;return(t=this.input)==null?void 0:t.focus()}}>
        <div class="scroll">
          ${this.lines.map(t=>a`
              <pre class=${t.kind}>${t.text}${t.elapsed!==void 0?a`<span class="elapsed">${t.elapsed} ms</span>`:c}</pre>
            `)}
        </div>

        ${this.suggestions.length?a`
              <div class="suggestions">
                ${this.suggestions.map(t=>a`
                    <button
                      class="chip"
                      @click=${()=>{var s;this.draft=`${t.name} `,this.suggestions=[],(s=this.input)==null||s.focus()}}
                    >
                      ${t.name}<span class="hint">${t.summary}</span>
                    </button>
                  `)}
              </div>
            `:c}

        <div class="prompt">
          <span class="sigil">❯</span>
          <input
            .value=${this.draft}
            ?disabled=${this.busy}
            placeholder=${this.busy?"working…":"investigate 1.1.1.1   ·   kev   ·   help"}
            autocomplete="off"
            spellcheck="false"
            @input=${this.onInput}
            @keydown=${this.onKey}
          />
          ${this.busy?a`<span class="spinner">▊</span>`:c}
        </div>
      </div>
    `}};r.styles=f`
    :host {
      display: block;
      height: 100%;
      font-family: var(--ds-font-mono, ui-monospace, "SFMono-Regular", Menlo, monospace);
      font-size: 0.8rem;
      color: rgba(200, 230, 245, 0.9);
    }
    .wrap { display: flex; flex-direction: column; height: 100%; min-height: 0; }

    .scroll {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      overflow-x: auto;
      padding: 12px 14px;
      line-height: 1.45;
      scrollbar-width: thin;
    }
    .scroll::-webkit-scrollbar { width: 8px; height: 8px; }
    .scroll::-webkit-scrollbar-thumb {
      background: rgba(120, 200, 230, 0.22); border-radius: 4px;
    }

    pre {
      margin: 0 0 10px;
      white-space: pre;
      font: inherit;
    }
    pre.input { color: rgba(150, 240, 200, 0.95); }
    pre.input::before { content: "❯ "; opacity: 0.6; }
    pre.output { color: rgba(200, 230, 245, 0.88); }
    pre.error { color: rgba(255, 150, 150, 0.95); }
    pre.system { color: rgba(140, 200, 230, 0.6); }

    .elapsed {
      display: block;
      margin-top: 2px;
      font-size: 0.68rem;
      opacity: 0.4;
    }

    .suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 6px 14px 0;
    }
    .chip {
      border: 1px solid rgba(120, 200, 230, 0.25);
      background: rgba(120, 200, 230, 0.07);
      border-radius: 3px;
      padding: 2px 7px;
      font-size: 0.7rem;
      cursor: pointer;
      color: inherit;
      font-family: inherit;
    }
    .chip:hover { background: rgba(120, 200, 230, 0.2); }
    .chip .hint { opacity: 0.5; margin-left: 6px; }

    .prompt {
      display: flex;
      align-items: center;
      gap: 8px;
      border-top: 1px solid rgba(120, 200, 230, 0.16);
      padding: 9px 14px;
    }
    .sigil { color: rgba(150, 240, 200, 0.8); }
    input {
      flex: 1;
      background: transparent;
      border: 0;
      outline: none;
      color: inherit;
      font: inherit;
      caret-color: rgba(150, 240, 200, 0.9);
    }
    input::placeholder { color: rgba(200, 230, 245, 0.32); }
    .spinner { opacity: 0.6; animation: blink 1s steps(2) infinite; }
    @keyframes blink { 50% { opacity: 0.15; } }
    @media (prefers-reduced-motion: reduce) { .spinner { animation: none; } }
  `;n([l()],r.prototype,"lines",2);n([l()],r.prototype,"draft",2);n([l()],r.prototype,"busy",2);n([l()],r.prototype,"commands",2);n([l()],r.prototype,"suggestions",2);n([d(".scroll")],r.prototype,"scroller",2);n([d("input")],r.prototype,"input",2);r=n([m("ops-terminal")],r);export{r as OpsTerminal};
//# sourceMappingURL=ops-terminal-AfOFjh1I.js.map
