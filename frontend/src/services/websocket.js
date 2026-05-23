import { useEffect, useRef, useState, useCallback } from 'react';

export const useWebSocket = (url) => {
  const [latestMessage, setLatestMessage] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef(null);

  const getBackoffDelay = (attempt) => {
    const delays = [3000, 6000, 12000, 30000];
    return delays[Math.min(attempt, delays.length - 1)];
  };

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('✅ WebSocket connected');
      reconnectAttempts.current = 0;
      setConnected(true);
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLatestMessage(data);
      } catch (err) {
        console.error('WebSocket received invalid JSON:', event.data);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };

    ws.onclose = () => {
      console.warn('⚠️ WebSocket disconnected');
      setConnected(false);
      const attempt = reconnectAttempts.current;
      const delay = getBackoffDelay(attempt);
      reconnectAttempts.current += 1;
      reconnectTimer.current = window.setTimeout(() => {
        console.log(`🔄 Reconnecting in ${delay / 1000}s...`);
        connect();
      }, delay);
    };
  }, [url]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected');
    }
  }, []);

  return { latestMessage, connected, sendMessage };
};
