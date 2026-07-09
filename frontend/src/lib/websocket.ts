/**
 * SentinelFlow AI — WebSocket Client
 * Premium client manager supporting reconnect backoffs, heartbeat keepalives,
 * outgoing message queues, and callback event registrations.
 */

type WebSocketCallback = (data: any) => void;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private session_id: string = '';
  private token: string = '';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private heartbeatInterval: any = null;
  private subscriptions: Map<string, Set<WebSocketCallback>> = new Map();
  private bufferedMessages: string[] = [];

  constructor() {
    if (typeof window !== 'undefined') {
      this.session_id = Math.random().toString(36).substring(2, 15);
    }
  }

  connect(token: string) {
    if (this.socket || !token) return;
    this.token = token;

    const wsUrl = `ws://127.0.0.1:8000/api/v1/ws/${this.session_id}?token=${token}`;
    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.debug(`[WS] Connected with session ${this.session_id}`);
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
      
      // Flush buffered messages
      while (this.bufferedMessages.length > 0) {
        const msg = this.bufferedMessages.shift();
        if (msg) this.socket?.send(msg);
      }

      this.startHeartbeat();
    };

    this.socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const { type, data } = payload;
        
        // Trigger specific type subscriptions
        const callbacks = this.subscriptions.get(type);
        if (callbacks) {
          callbacks.forEach(cb => cb(data));
        }

        // Wildcard subscriptions
        const wildcards = this.subscriptions.get('*');
        if (wildcards) {
          wildcards.forEach(cb => cb({ type, data }));
        }
      } catch (err) {
        console.error('[WS] Failed to parse message payload:', err);
      }
    };

    this.socket.onclose = (event) => {
      console.debug(`[WS] Connection closed: ${event.reason || 'Closed without reason'}`);
      this.cleanup();
      this.attemptReconnect();
    };

    this.socket.onerror = (err) => {
      console.error('[WS] Socket error occurred:', err);
    };
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.send({ action: 'ping' });
    }, 30000);
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WS] Max reconnect attempts exceeded. Halting retries.');
      return;
    }
    this.reconnectAttempts++;
    console.debug(`[WS] Reconnecting attempt ${this.reconnectAttempts} in ${this.reconnectDelay}ms...`);
    setTimeout(() => {
      this.reconnectDelay *= 2;
      this.connect(this.token);
    }, this.reconnectDelay);
  }

  send(message: any) {
    const raw = JSON.stringify(message);
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(raw);
    } else {
      this.bufferedMessages.push(raw);
    }
  }

  subscribe(type: string, callback: WebSocketCallback) {
    if (!this.subscriptions.has(type)) {
      this.subscriptions.set(type, new Set());
    }
    this.subscriptions.get(type)!.add(callback);
    
    // If subscribing to incident id feeds, instruct the manager
    if (type.startsWith('incident:')) {
      const incidentId = parseInt(type.split(':')[1], 10);
      this.send({ action: 'subscribe', incident_id: incidentId });
    }

    return () => this.unsubscribe(type, callback);
  }

  unsubscribe(type: string, callback: WebSocketCallback) {
    const callbacks = this.subscriptions.get(type);
    if (callbacks) {
      callbacks.delete(callback);
      if (callbacks.size === 0) {
        this.subscriptions.delete(type);
        if (type.startsWith('incident:')) {
          const incidentId = parseInt(type.split(':')[1], 10);
          this.send({ action: 'unsubscribe', incident_id: incidentId });
        }
      }
    }
  }

  disconnect() {
    this.cleanup();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  private cleanup() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}

export const wsClient = new WebSocketClient();
