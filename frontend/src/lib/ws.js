// Lightweight WebSocket client with auto-reconnect.
const BACKEND = process.env.REACT_APP_BACKEND_URL || "https://fidem-backend-production.up.railway.app";

export class WS {
  constructor({ onMessage, onOpen, onClose }) {
    this.onMessage = onMessage || (() => {});
    this.onOpen = onOpen || (() => {});
    this.onClose = onClose || (() => {});
    this.sock = null;
    this.shouldRun = false;
    this.reconnectAttempt = 0;
    this.pingInterval = null;
  }
  start(token) {
    if (!token) return;
    this.shouldRun = true;
    this._open(token);
  }
  stop() {
    this.shouldRun = false;
    if (this.pingInterval) { clearInterval(this.pingInterval); this.pingInterval = null; }
    try { this.sock && this.sock.close(); } catch {}
    this.sock = null;
  }
  _open(token) {
    if (!this.shouldRun) return;
    const wsScheme = BACKEND.startsWith("https") ? "wss" : "ws";
    const wsBase = BACKEND.replace(/^https?:/, `${wsScheme}:`);
    const url = `${wsBase}/api/ws?token=${encodeURIComponent(token)}`;
    let sock;
    try {
      sock = new WebSocket(url);
    } catch (e) {
      console.warn("WebSocket connection failed:", e);
      this._scheduleReconnect(token);
      return;
    }
    this.sock = sock;
    sock.onopen = () => {
      this.reconnectAttempt = 0;
      this.onOpen();
      this.pingInterval = setInterval(() => {
        try { sock.readyState === 1 && sock.send("ping"); } catch {}
      }, 25000);
    };
    sock.onmessage = (evt) => {
      if (evt.data === "pong") return;
      try {
        const m = JSON.parse(evt.data);
        this.onMessage(m);
      } catch (e) {
        console.warn("WebSocket message parse error:", e);
      }
    };
    sock.onerror = (e) => {
      console.warn("WebSocket error:", e);
    };
    sock.onclose = () => {
      if (this.pingInterval) { clearInterval(this.pingInterval); this.pingInterval = null; }
      this.onClose();
      this._scheduleReconnect(token);
    };
  }
  _scheduleReconnect(token) {
    if (!this.shouldRun) return;
    this.reconnectAttempt += 1;
    const delay = Math.min(30000, 1000 * Math.pow(2, this.reconnectAttempt));
    setTimeout(() => this._open(token), delay);
  }
}
