import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

interface Drop {
  col: number;
  row: number; // float
  speed: number;
  length: number;
}

interface GridCell {
  char: string;
  locked: boolean; // if true, won't mutate (used for system words)
}

@customElement("matrix-waterfall")
export class MatrixWaterfall extends LitElement {
  @property({ attribute: false }) activity = 0;
  @property({ attribute: false }) status = "idle";

  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private raf = 0;
  private w = 0; private h = 0;
  
  private fontSize = 16;
  private columns = 0;
  private rows = 0;
  
  private grid: GridCell[][] = [];
  private drops: Drop[] = [];
  
  private sysWords = [
    "BREACH_DETECTED", "IP:167.94.146.68", "SYS.OVERRIDE", "ACCESS_GRANTED",
    "MEM_VAULT", "OSINT_QUERY_ACTIVE", "0xDEADBEEF", "ROOT_KITTEN", "SANS_ISC"
  ];

  static styles = css`
    :host { 
      display: block; width: 100%; height: 100%; position: relative; 
      background: #000; overflow: hidden; pointer-events: none;
    }
    canvas { 
      width: 100%; height: 100%; display: block; 
    }
    .overlay {
      position: absolute; inset: 0; pointer-events: none;
      background: radial-gradient(circle at center, transparent 10%, rgba(0,0,20,0.5) 100%);
    }
  `;

  firstUpdated() {
    this.canvas = this.renderRoot.querySelector("canvas")!;
    this.ctx = this.canvas.getContext("2d", { alpha: false })!;
    
    new ResizeObserver(() => this._resize()).observe(this);
    this._resize();
    this.raf = requestAnimationFrame((ts) => this._loop(ts));
    
    this._fetchThreats();
    setInterval(() => this._fetchThreats(), 15000);
    
    // Periodically inject system words
    setInterval(() => this._injectWord(), 3000);
  }

  private async _fetchThreats() {
    try {
      const res = await fetch("/api/threats/live");
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        for(let i=0; i<3; i++) {
          const t = data[Math.floor(Math.random() * data.length)];
          if (t && t.ip && !this.sysWords.includes(`IP:${t.ip}`)) {
            this.sysWords.push(`IP:${t.ip}`);
            if (t.country) this.sysWords.push(`TRGT:${t.country.substring(0,8).toUpperCase()}`);
          }
        }
      }
    } catch (e) {}
  }

  private _resize() {
    if (!this.canvas) return;
    this.w = this.clientWidth || window.innerWidth;
    this.h = this.clientHeight || window.innerHeight;
    this.canvas.width = this.w;
    this.canvas.height = this.h;
    
    this.columns = Math.ceil(this.w / this.fontSize);
    this.rows = Math.ceil(this.h / this.fontSize);
    
    // Initialize Grid
    this.grid = [];
    for (let c = 0; c < this.columns; c++) {
      this.grid[c] = [];
      for (let r = 0; r < this.rows; r++) {
        this.grid[c][r] = { char: this._randomChar(), locked: false };
      }
    }
    
    // Initialize Drops
    this.drops = [];
    const numDrops = Math.floor(this.columns * 1.5); // High density
    for (let i = 0; i < numDrops; i++) {
      this.drops.push(this._createDrop());
    }
  }
  
  private _createDrop(): Drop {
    return {
      col: Math.floor(Math.random() * this.columns),
      row: Math.random() * -this.rows,
      speed: Math.random() * 0.8 + 0.3,
      length: Math.floor(Math.random() * 25) + 10
    };
  }

  private _randomChar() {
    // True Matrix uses Half-width Katakana + Latin
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$+-*/=%\"'#&_(),.;:?!\\|{}<>[]^~ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ";
    return chars.charAt(Math.floor(Math.random() * chars.length));
  }
  
  private _injectWord() {
    if (!this.grid.length) return;
    const word = this.sysWords[Math.floor(Math.random() * this.sysWords.length)];
    const col = Math.floor(Math.random() * this.columns);
    const startRow = Math.floor(Math.random() * (this.rows - word.length));
    
    for (let i = 0; i < word.length; i++) {
      if (this.grid[col] && this.grid[col][startRow + i]) {
        this.grid[col][startRow + i].char = word[i];
        this.grid[col][startRow + i].locked = true;
        
        // unlock after a while
        setTimeout(() => {
          if (this.grid[col] && this.grid[col][startRow + i]) {
            this.grid[col][startRow + i].locked = false;
          }
        }, 8000);
      }
    }
  }

  private _loop(ts: number) {
    this.raf = requestAnimationFrame((t) => this._loop(t));
    if (!this.ctx) return;
    
    // Full clear. No messy trails.
    this.ctx.fillStyle = '#000';
    this.ctx.fillRect(0, 0, this.w, this.h);

    // Determine theme color
    // Default cyan: 0, 255, 255
    let r = 0, g = 255, b = 255; 
    if (this.status === 'warning') { r = 255; g = 0; b = 60; }
    else if (this.status === 'speaking') { r = 255; g = 176; b = 0; }
    else if (this.activity > 0.5) { r = 0; g = 255; b = 65; }

    this.ctx.font = `bold ${this.fontSize * 0.9}px monospace`;
    this.ctx.textAlign = "center";
    this.ctx.textBaseline = "middle";

    // Randomly mutate unlocked grid cells (glitch effect)
    const mutations = Math.floor(this.columns * this.rows * 0.05);
    for (let i = 0; i < mutations; i++) {
      const mc = Math.floor(Math.random() * this.columns);
      const mr = Math.floor(Math.random() * this.rows);
      if (this.grid[mc] && this.grid[mc][mr] && !this.grid[mc][mr].locked) {
        this.grid[mc][mr].char = this._randomChar();
      }
    }

    // Render drops
    for (const drop of this.drops) {
      drop.row += drop.speed * (this.status === 'thinking' ? 2 : 1);
      
      const headRow = Math.floor(drop.row);
      const x = drop.col * this.fontSize + (this.fontSize / 2);
      
      for (let i = 0; i < drop.length; i++) {
        const rIdx = headRow - i;
        if (rIdx < 0 || rIdx >= this.rows) continue;
        
        const cell = this.grid[drop.col][rIdx];
        if (!cell) continue;
        
        const y = rIdx * this.fontSize + (this.fontSize / 2);
        
        if (i === 0) {
          // Head (Bright White)
          this.ctx.fillStyle = '#FFF';
          this.ctx.shadowBlur = 12;
          this.ctx.shadowColor = `rgb(${r}, ${g}, ${b})`;
          this.ctx.fillText(cell.char, x, y);
          this.ctx.shadowBlur = 0;
        } else {
          // Trail (Fading Color)
          const opacity = Math.max(0, 1 - (i / drop.length));
          // If locked (system word), make it pop out more
          if (cell.locked) {
            this.ctx.fillStyle = `rgba(255, 255, 255, ${opacity * 0.9})`;
            this.ctx.shadowBlur = 5;
            this.ctx.shadowColor = `rgb(${r}, ${g}, ${b})`;
          } else {
            this.ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${opacity})`;
            this.ctx.shadowBlur = 0;
          }
          this.ctx.fillText(cell.char, x, y);
          this.ctx.shadowBlur = 0;
        }
      }
      
      // Reset drop if it fully exits the screen
      if (headRow - drop.length > this.rows) {
        drop.row = -Math.random() * 20;
        drop.col = Math.floor(Math.random() * this.columns);
        drop.speed = Math.random() * 0.8 + 0.3;
        drop.length = Math.floor(Math.random() * 25) + 10;
      }
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    cancelAnimationFrame(this.raf);
  }
  
  render() { 
    return html`
      <canvas></canvas>
      <div class="overlay"></div>
    `; 
  }
}

declare global {
  interface HTMLElementTagNameMap { "matrix-waterfall": MatrixWaterfall; }
}
