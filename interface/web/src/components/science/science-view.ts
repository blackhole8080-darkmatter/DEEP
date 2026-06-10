// <science-view> — the science oracle surface: periodic table (118 elements,
// category-shaded, click → verified data) + physics constants & formulas.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import {
  fetchPeriodicTable, fetchElement, fetchPhysicsConstants, fetchPhysicsFormulas,
  type ElementInfo,
} from "../../core/api";
import "../primitives/ds-panel";

function gridPos(e: ElementInfo): { row: number; col: number } | null {
  const z = e.atomic_number;
  if (z >= 57 && z <= 71) return { row: 9, col: 3 + (z - 57) };
  if (z >= 89 && z <= 103) return { row: 10, col: 3 + (z - 89) };
  if (e.group && e.period) return { row: e.period, col: e.group };
  return null;
}

@customElement("science-view")
export class ScienceView extends LitElement {
  @state() private elements: ElementInfo[] = [];
  @state() private detail: ElementInfo | null = null;
  @state() private constants: { name: string; value: number; unit: string; symbol: string }[] = [];
  @state() private formulas: { name: string; era: string; domain: string; formula: string }[] = [];

  connectedCallback(): void {
    super.connectedCallback();
    void fetchPeriodicTable().then((d) => (this.elements = d.elements)).catch(() => {});
    void fetchPhysicsConstants().then((d) => (this.constants = d.constants)).catch(() => {});
    void fetchPhysicsFormulas().then((d) => (this.formulas = d.formulas)).catch(() => {});
  }

  static styles = css`
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
  `;

  private async pick(z: number): Promise<void> {
    const d = await fetchElement(z).catch(() => null);
    if (d?.ok && d.element) this.detail = d.element;
  }

  private renderDetail() {
    const e = this.detail;
    if (!e) return html`<span style="color:var(--ds-text-muted)">Select an element for verified data.</span>`;
    const row = (k: string, v: unknown) =>
      v == null ? "" : html`<div class="row"><span>${k}</span><b>${v}</b></div>`;
    return html`
      <div class="detail">
        <span class="title">${e.name} (${e.symbol}) · Z=${e.atomic_number}</span>
        ${row("Atomic weight", e.atomic_weight)}
        ${row("Electron config", e.electron_configuration)}
        ${row("Electronegativity", e["electronegativity"])}
        ${row("Oxidation states", Array.isArray(e["oxidation_states"]) ? (e["oxidation_states"] as number[]).join(", ") : null)}
        ${row("Melting point (K)", e["melting_point_K"])}
        ${row("Boiling point (K)", e["boiling_point_K"])}
        ${row("Density (g/cm³)", e["density_g_cm3"])}
        ${row("Category", e.series)}
        ${row("Discovered", e["discovery_year"])}
      </div>
    `;
  }

  render() {
    return html`
      <ds-panel heading="Periodic table · ${this.elements.length} elements · curated data">
        <div class="grid">
          ${this.elements.map((e) => {
            const p = gridPos(e);
            if (!p) return "";
            return html`
              <button class="cell cat-${e.category}" title=${e.name}
                style="grid-row:${p.row};grid-column:${p.col}"
                @click=${() => void this.pick(e.atomic_number)}>
                <span class="z">${e.atomic_number}</span>
                <span class="sym">${e.symbol}</span>
              </button>
            `;
          })}
        </div>
        <div style="margin-top:var(--ds-space-4)">${this.renderDetail()}</div>
      </ds-panel>

      <div class="cols">
        <ds-panel heading="Physical constants · CODATA">
          <div class="list mono">
            ${this.constants.map(
              (c) => html`<div class="row"><span>${c.name} (${c.symbol})</span><b>${c.value} ${c.unit}</b></div>`,
            )}
          </div>
        </ds-panel>
        <ds-panel heading="Formula library · ancient → modern">
          <div class="list mono">
            ${this.formulas.map(
              (f) => html`<div class="row"><span>${f.name} <span class="era">${f.era}</span></span><b>${f.formula}</b></div>`,
            )}
          </div>
        </ds-panel>
      </div>
    `;
  }
}
