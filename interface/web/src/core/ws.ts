// Typed, auto-reconnecting WebSocket client for DEEP.
// Phase 0: connection + message bus. Grows into the full typed protocol later.

export interface DeepMessage {
  type: string;
  [key: string]: unknown;
}

type Handler = (msg: DeepMessage) => void;

export class DeepSocket {
  private ws: WebSocket | null = null;
  private handlers = new Set<Handler>();
  private url: string;
  private reconnectDelay = 1000;
  private readonly maxDelay = 15000;
  private closedByUser = false;

  status: "connecting" | "open" | "closed" = "closed";

  constructor(path = "/ws/deep") {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    // In Vite dev the proxy forwards /ws; in prod we're same-origin.
    this.url = `${proto}://${location.host}${path}`;
  }

  connect(): void {
    this.closedByUser = false;
    this.status = "connecting";
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.status = "open";
      this.reconnectDelay = 1000;
      this.emit({ type: "_socket_open" });
    };
    this.ws.onmessage = (e) => {
      try {
        this.emit(JSON.parse(e.data) as DeepMessage);
      } catch {
        /* ignore non-JSON frames */
      }
    };
    this.ws.onclose = () => {
      this.status = "closed";
      this.emit({ type: "_socket_close" });
      if (!this.closedByUser) this.scheduleReconnect();
    };
    this.ws.onerror = () => this.ws?.close();
  }

  private scheduleReconnect(): void {
    setTimeout(() => this.connect(), this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 1.6, this.maxDelay);
  }

  send(msg: DeepMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(msg));
  }

  on(handler: Handler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  private emit(msg: DeepMessage): void {
    for (const h of this.handlers) h(msg);
  }

  close(): void {
    this.closedByUser = true;
    this.ws?.close();
  }
}

export const socket = new DeepSocket();
