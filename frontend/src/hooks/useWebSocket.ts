import { useEffect } from 'react';
import { wsClient } from '../lib/websocket';

/**
 * Custom React hook for subscribing to real-time WebSocket events.
 * Handles auto-connection checks and callback listeners cleanup lifecycle.
 */
export function useWebSocket(type: string, callback: (data: any) => void) {
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('sf_token');
      if (token) {
        wsClient.connect(token);
      }
    }

    const unsubscribe = wsClient.subscribe(type, callback);
    return () => {
      unsubscribe();
    };
  }, [type, callback]);
}
