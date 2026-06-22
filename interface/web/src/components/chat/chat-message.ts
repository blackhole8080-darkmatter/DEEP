// <chat-message> — one message bubble. AI text renders as sanitized markdown;
// streaming shows a caret; finished AI messages show a model/latency badge.
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { marked } from "marked";
import DOMPurify from "dompurify";
import type { ChatMessage } from "../../core/store";
import { katexStyles, renderTeX } from "../../core/math";
import "./reasoning-trail";

marked.setOptions({ breaks: true, gfm: true });

// Render markdown, typesetting any LaTeX ($$…$$, \[…\] display; $…$, \(…\) inline)
// with KaTeX. Math is pulled out first so marked/DOMPurify can't mangle it, then
// the trusted KaTeX HTML is spliced back in after sanitization.
function renderMarkdown(text: string): string {
  const math: string[] = [];
  const stash = (tex: string, display: boolean) => {
    const i = math.push(renderTeX(tex.trim(), display)) - 1;
    return ` @@MATH${i}@@ `;
  };
  const protectedText = text
    .replace(/\$\$([\s\S]+?)\$\$/g, (_m, t) => stash(t, true))
    .replace(/\\\[([\s\S]+?)\\\]/g, (_m, t) => stash(t, true))
    .replace(/\\\(([\s\S]+?)\\\)/g, (_m, t) => stash(t, false))
    .replace(/(?<![\\$])\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)/g, (_m, t) => stash(t, false));
  let htmlOut = DOMPurify.sanitize(marked.parse(protectedText, { async: false }) as string);
  htmlOut = htmlOut.replace(/@@MATH(\d+)@@/g, (_m, i) => math[+i] ?? "");
  return htmlOut;
}

@customElement("chat-message")
export class ChatMessageEl extends LitElement {
  @property({ attribute: false }) msg!: ChatMessage;

  static styles = [katexStyles, css`
    :host { display: grid; }
    .md .katex { color: var(--ds-text); }
    .md .katex-display { margin: var(--ds-space-3) 0; overflow-x: auto; overflow-y: hidden; }
    .bubble {
      padding: var(--ds-space-3) var(--ds-space-4);
      border-radius: var(--ds-radius-md);
      border: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
      line-height: var(--ds-leading-normal);
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
      overflow-wrap: anywhere;
    }
    .user {
      background: rgba(var(--ds-periwinkle-rgb), 0.10);
      border-color: var(--ds-border-accent);
      justify-self: end;
      max-width: 85%;
      white-space: pre-wrap;
    }
    .ai { background: var(--ds-surface-1); justify-self: start; max-width: 94%; }
    .ai.streaming .md::after {
      content: "▋"; color: var(--ds-accent); animation: blink 1s steps(1) infinite;
    }
    .md :first-child { margin-top: 0; }
    .md :last-child { margin-bottom: 0; }
    .md p { margin: var(--ds-space-2) 0; }
    .md code {
      font-family: var(--ds-font-mono); font-size: 0.85em;
      background: var(--ds-surface-2); padding: 1px 5px;
      border-radius: var(--ds-radius-xs); color: var(--ds-accent);
    }
    .md pre {
      background: var(--ds-charcoal-900); border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-sm); padding: var(--ds-space-3);
      overflow-x: auto;
    }
    .md pre code { background: none; padding: 0; color: var(--ds-text); }
    .md ul, .md ol { padding-left: var(--ds-space-5); margin: var(--ds-space-2) 0; }
    .md a { color: var(--ds-accent); }
    .md table { border-collapse: collapse; margin: var(--ds-space-2) 0; }
    .md th, .md td { border: 1px solid var(--ds-border); padding: var(--ds-space-1) var(--ds-space-3); }
    .md blockquote {
      margin: var(--ds-space-2) 0; padding-left: var(--ds-space-3);
      border-left: 2px solid var(--ds-border-accent); color: var(--ds-text-soft);
    }
    img.attached {
      display: block; max-width: 280px; max-height: 240px;
      border-radius: var(--ds-radius-sm); border: 1px solid var(--ds-border);
      margin-bottom: var(--ds-space-2);
    }
    .badge {
      margin-top: var(--ds-space-2);
      font-family: var(--ds-font-mono);
      font-size: 0.65rem;
      color: var(--ds-text-faint);
    }
    reasoning-trail { display: block; margin-top: var(--ds-space-2); }
    @keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
    @keyframes blink { 50% { opacity: 0; } }
    @media (prefers-reduced-motion: reduce) { .bubble { animation: none; } }
  `];

  render() {
    const m = this.msg;
    if (m.role === "user") {
      return html`
        <div class="bubble user">
          ${m.image ? html`<img class="attached" src=${m.image} alt="attached" />` : ""}${m.text}
        </div>
      `;
    }
    const badge =
      !m.streaming && (m.model || m.latency)
        ? html`<div class="badge">
            ${m.model ?? ""}${m.latency ? ` · ${m.latency < 1000 ? `${m.latency}ms` : `${(m.latency / 1000).toFixed(1)}s`}` : ""}
          </div>`
        : "";
    return html`
      <div class="bubble ai ${m.streaming ? "streaming" : ""}">
        <div class="md">${unsafeHTML(renderMarkdown(m.text))}</div>
        ${m.reasoning?.length
          ? html`<reasoning-trail .steps=${m.reasoning} .startCollapsed=${true}></reasoning-trail>`
          : ""}
        ${badge}
      </div>
    `;
  }
}
