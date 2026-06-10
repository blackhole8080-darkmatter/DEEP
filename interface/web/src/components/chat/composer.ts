// <chat-composer> — auto-growing textarea + image attach (button/paste/drop)
// + document drop (→ knowledge ingestion). Emits `send` {text, image}.
import { LitElement, html, css } from "lit";
import { customElement, state, query } from "lit/decorators.js";
import { ingestDocument } from "../../core/api";
import { toast } from "../primitives/ds-toast";
import "../primitives/ds-button";

const MAX_DIM = 1280;

async function downscale(dataUrl: string): Promise<string> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      let { width: w, height: h } = img;
      if (Math.max(w, h) > MAX_DIM) {
        const s = MAX_DIM / Math.max(w, h);
        w = Math.round(w * s); h = Math.round(h * s);
      }
      const c = document.createElement("canvas");
      c.width = w; c.height = h;
      c.getContext("2d")!.drawImage(img, 0, 0, w, h);
      try { resolve(c.toDataURL("image/jpeg", 0.85)); } catch { resolve(dataUrl); }
    };
    img.onerror = () => resolve(dataUrl);
    img.src = dataUrl;
  });
}

@customElement("chat-composer")
export class ChatComposer extends LitElement {
  @state() private image: string | null = null;
  @state() private dragging = false;
  @query("textarea") private ta!: HTMLTextAreaElement;

  static styles = css`
    :host { display: block; }
    .wrap {
      display: flex; gap: var(--ds-space-2); align-items: flex-end;
      padding: var(--ds-space-2);
      background: var(--ds-surface-1);
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      transition: border-color var(--ds-dur-fast) var(--ds-ease-out);
    }
    .wrap:focus-within { border-color: var(--ds-border-accent); }
    .wrap.dragging { outline: 1.5px dashed var(--ds-accent); outline-offset: 2px; }
    textarea {
      flex: 1; resize: none; border: 0; background: none; outline: none;
      color: var(--ds-text); font-family: var(--ds-font-sans);
      font-size: var(--ds-text-sm); line-height: var(--ds-leading-normal);
      max-height: 180px; padding: var(--ds-space-2);
    }
    textarea::placeholder { color: var(--ds-text-faint); }
    .icon-btn {
      display: grid; place-items: center;
      width: 34px; height: 34px; flex: none;
      border: 0; border-radius: var(--ds-radius-sm);
      background: none; color: var(--ds-text-muted); cursor: pointer;
      transition: color var(--ds-dur-fast), background var(--ds-dur-fast);
    }
    .icon-btn:hover { color: var(--ds-accent); background: rgba(var(--ds-periwinkle-rgb), 0.1); }
    .chip {
      display: inline-flex; align-items: center; gap: var(--ds-space-2);
      margin-bottom: var(--ds-space-2);
      padding: var(--ds-space-1) var(--ds-space-2);
      background: var(--ds-glass);
      border: 1px solid var(--ds-border);
      border-left: 2px solid var(--ds-accent);
      border-radius: var(--ds-radius-sm);
      font-size: var(--ds-text-xs); color: var(--ds-text-soft);
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
    }
    .chip img { width: 26px; height: 26px; object-fit: cover; border-radius: var(--ds-radius-xs); }
    .chip button { border: 0; background: none; color: var(--ds-text-muted); cursor: pointer; }
    .chip button:hover { color: var(--ds-danger); }
    @keyframes rise { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  `;

  firstUpdated(): void {
    document.addEventListener("paste", this.onPaste);
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    document.removeEventListener("paste", this.onPaste);
  }

  private onPaste = (e: ClipboardEvent) => {
    for (const it of e.clipboardData?.items ?? []) {
      if (it.type.startsWith("image/")) {
        const f = it.getAsFile();
        if (f) void this.stageImage(f);
        return;
      }
    }
  };

  private async stageImage(file: File): Promise<void> {
    const raw = await new Promise<string>((res) => {
      const fr = new FileReader();
      fr.onload = () => res(fr.result as string);
      fr.readAsDataURL(file);
    });
    this.image = await downscale(raw);
  }

  private async onDrop(e: DragEvent): Promise<void> {
    e.preventDefault();
    this.dragging = false;
    const f = e.dataTransfer?.files?.[0];
    if (!f) return;
    if (f.type.startsWith("image/")) return void this.stageImage(f);
    // Document → knowledge ingestion
    toast(`Ingesting ${f.name}…`, "info");
    const r = await ingestDocument(f);
    if (r.ok) toast(`Absorbed ${r.source} (${r.chunks} chunks)`, "success");
    else toast(`Ingest failed: ${r.error ?? "unknown"}`, "danger");
  }

  private autoGrow(): void {
    this.ta.style.height = "auto";
    this.ta.style.height = `${Math.min(this.ta.scrollHeight, 180)}px`;
  }

  private fire(): void {
    const text = this.ta.value.trim();
    if (!text && !this.image) return;
    this.dispatchEvent(new CustomEvent("send", {
      detail: { text, image: this.image },
      bubbles: true, composed: true,
    }));
    this.ta.value = "";
    this.image = null;
    this.autoGrow();
  }

  private onKey(e: KeyboardEvent): void {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); this.fire(); }
  }

  private pickFile(accept: string, handler: (f: File) => void): void {
    const inp = document.createElement("input");
    inp.type = "file"; inp.accept = accept;
    inp.onchange = () => inp.files?.[0] && handler(inp.files[0]);
    inp.click();
  }

  render() {
    return html`
      ${this.image
        ? html`<span class="chip">
            <img src=${this.image} alt="staged" />
            image attached · sent to vision
            <button @click=${() => (this.image = null)} aria-label="Remove">✕</button>
          </span>`
        : ""}
      <div
        class="wrap ${this.dragging ? "dragging" : ""}"
        @dragover=${(e: DragEvent) => { e.preventDefault(); this.dragging = true; }}
        @dragleave=${() => (this.dragging = false)}
        @drop=${this.onDrop}
      >
        <button class="icon-btn" title="Attach image (vision)"
          @click=${() => this.pickFile("image/*", (f) => void this.stageImage(f))}>🖼</button>
        <button class="icon-btn" title="Ingest document into memory"
          @click=${() => this.pickFile(".pdf,.txt,.md,.py,.js,.ts,.json", async (f) => {
            toast(`Ingesting ${f.name}…`, "info");
            const r = await ingestDocument(f);
            r.ok ? toast(`Absorbed ${r.source} (${r.chunks} chunks)`, "success")
                 : toast(`Ingest failed: ${r.error ?? "unknown"}`, "danger");
          })}>📎</button>
        <textarea rows="1" placeholder="Message DEEP…"
          @input=${this.autoGrow} @keydown=${this.onKey}></textarea>
        <ds-button variant="primary" @click=${this.fire}>Send</ds-button>
      </div>
    `;
  }
}
