// Speech — the consumer for `tts_speak`, which until now had none.
//
// Ten places in the backend publish `tts_speak`: the boot announcement, the
// morning briefing, anomaly warnings, threat classifications, Tailscale
// events, chat replies, and now the alert dispatcher's voice channel. The
// server-side voice package was deleted and the HUD never implemented one, so
// every one of those announcements has been travelling over the WebSocket and
// falling on the floor. This module is the missing half.
//
// Synthesis happens here rather than on the server on purpose: speech belongs
// where the speakers are, and a headless DEEP on a server has no business
// trying to talk. The consequence is that voice only reaches a machine with
// the HUD open — it complements the desktop notification, which survives a
// closed tab, rather than replacing it.
//
// Three rules keep it from becoming the thing you mute permanently:
//   * Muting persists. A voice you can only silence until reload is one people
//     turn off at the source, and then the alerts go too.
//   * `urgent` interrupts, `normal` queues. Talking over yourself is worse
//     than waiting, and a critical alert that politely waits behind a morning
//     briefing is not critical.
//   * A backlog is dropped, not queued. Coming back to a tab that has been
//     accumulating announcements for an hour should not mean listening to an
//     hour of them.
import { signal } from "@lit-labs/signals";
import { socket } from "./ws";

const MUTE_KEY = "deep.speech.muted";
/** Past this many waiting utterances, the oldest are dropped. */
const MAX_QUEUE = 3;

export const speechMuted = signal(readMuted());
/** False when the browser has no speech synthesis at all. */
export const speechAvailable = signal(
  typeof window !== "undefined" && "speechSynthesis" in window,
);

function readMuted(): boolean {
  try {
    return localStorage.getItem(MUTE_KEY) === "1";
  } catch {
    return false; // private mode, storage disabled — default to audible
  }
}

export function setMuted(muted: boolean): void {
  speechMuted.set(muted);
  try {
    localStorage.setItem(MUTE_KEY, muted ? "1" : "0");
  } catch {
    /* not persisting is survivable; not muting is not */
  }
  if (muted) cancel();
}

export function toggleMuted(): boolean {
  const next = !speechMuted.get();
  setMuted(next);
  return next;
}

export function cancel(): void {
  outstanding = 0;
  try {
    window.speechSynthesis?.cancel();
  } catch {
    /* nothing to cancel */
  }
}

// The Web Speech API exposes `pending` as a boolean, never a queue length, so
// the depth is counted here. Without it a burst of alerts queues without
// bound and the tab talks for minutes.
let outstanding = 0;

/** Say something. `urgent` cuts off whatever is being said. */
export function speak(text: string, priority: "normal" | "urgent" = "normal"): void {
  const said = (text ?? "").trim();
  if (!said || speechMuted.get() || !speechAvailable.get()) return;

  const synth = window.speechSynthesis;
  if (priority === "urgent") {
    synth.cancel();
    outstanding = 0;
  } else if (outstanding >= MAX_QUEUE) {
    // A backlog has built up — a tab left open through a noisy hour. Drop it
    // and say only the newest: stale announcements are worse than missing
    // ones, and nobody wants to sit through the queue to reach the current
    // thing.
    synth.cancel();
    outstanding = 0;
  }

  try {
    const utterance = new SpeechSynthesisUtterance(said);
    utterance.rate = 1.05;
    outstanding++;
    const done = () => { outstanding = Math.max(0, outstanding - 1); };
    utterance.onend = done;
    utterance.onerror = done;
    synth.speak(utterance);
  } catch {
    // Some browsers throw when synthesis is blocked before any user gesture.
    // Silence is the correct outcome; a thrown error in the WS handler is not.
    outstanding = Math.max(0, outstanding - 1);
  }
}

/** Outstanding utterance count. Exposed for tests. */
export function queueDepth(): number {
  return outstanding;
}

let wired = false;

/** Subscribe to `tts_speak`. Idempotent; called once from initStore. */
export function initSpeech(): void {
  if (wired) return;
  wired = true;
  socket.on((msg) => {
    const m = msg as { type?: string; payload?: { text?: string; priority?: string } };
    if (m.type !== "tts_speak") return;
    const payload = m.payload ?? {};
    speak(String(payload.text ?? ""), payload.priority === "urgent" ? "urgent" : "normal");
  });
}
