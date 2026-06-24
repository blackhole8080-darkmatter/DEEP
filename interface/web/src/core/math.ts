// math.ts — KaTeX rendering helpers for DEEP.
// Typesets verified LaTeX from the symbolic/science engines, and renders chat
// markdown with inline ($…$, \(…\)) and display ($$…$$, \[…\]) math. KaTeX runs
// fully offline (no network), matching DEEP's offline-first design.
import katex from "katex";
import katexCssText from "katex/dist/katex.min.css?inline";
import "katex/dist/contrib/mhchem.mjs";
import { css, unsafeCSS } from "lit";

// KaTeX stylesheet as a Lit `css` literal so components that render math can
// pull it into their shadow root via `static styles = [katexStyles, …]`.
export const katexStyles = css`${unsafeCSS(katexCssText)}`;

// Render a single LaTeX string to an HTML string. Never throws — on a parse
// error it returns the raw TeX in an error span so the UI degrades gracefully.
export function renderTeX(tex: string, displayMode = true): string {
  try {
    return katex.renderToString(tex, {
      displayMode,
      throwOnError: false,
      output: "html",
      strict: false,
    });
  } catch {
    return `<span class="tex-error">${escapeHtml(tex)}</span>`;
  }
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
}

// Replace math delimiters in a plain-text string with rendered KaTeX HTML.
// Order matters: display ($$…$$, \[…\]) before inline ($…$, \(…\)).
export function renderMathInText(text: string): string {
  return text
    .replace(/\$\$([\s\S]+?)\$\$/g, (_m, tex) => renderTeX(tex.trim(), true))
    .replace(/\\\[([\s\S]+?)\\\]/g, (_m, tex) => renderTeX(tex.trim(), true))
    .replace(/\\\(([\s\S]+?)\\\)/g, (_m, tex) => renderTeX(tex.trim(), false))
    .replace(/(?<![\\$])\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)/g, (_m, tex) =>
      renderTeX(tex.trim(), false));
}

// Quick check so callers can skip the regex passes when there's no math.
export function hasMath(text: string): boolean {
  return /\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|(?<![\\$])\$[^$\n]+?\$/.test(text);
}
