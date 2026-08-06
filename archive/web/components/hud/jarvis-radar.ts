// <jarvis-radar> — reserved radar widget (integrated into jarvis-core canvas)
import { LitElement } from "lit";
import { customElement } from "lit/decorators.js";

@customElement("jarvis-radar")
export class JarvisRadar extends LitElement {}

declare global { interface HTMLElementTagNameMap { "jarvis-radar": JarvisRadar; } }
