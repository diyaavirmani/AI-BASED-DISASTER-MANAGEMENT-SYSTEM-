
import { useEffect, useRef, useState, useCallback } from "react";


// --------------------------------------------------
// 172. CUSTOM HOOK
// --------------------------------------------------
export const useWebSocket = (url) => {
  const [latestMessage, setLatestMessage] = useState(null);
  const wsRef = useRef(null);
  const reconnectAttempts = useRef(0);

  // --------------------------------------------------
  // 174. EXPONENTIAL BACKOFF DELAYS
  // --------------------------------------------------
  const getBackoffDelay = () => {
    const delays = [3000, 6000, 12000, 30000]; // 3s → 30s
    return delays[Math.min(reconnectAttempts.current, delays.length - 1)];
  };

  // --------------------------------------------------
  // CONNECT FUNCTION
  // --------------------------------------------------
  const connect = useCallback(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    // ---------------------------
    // ON OPEN
    // ---------------------------
    ws.onopen = () => {
      console.log("✅ WebSocket connected");
      reconnectAttempts.current = 0; // reset backoff
    };

    // ---------------------------
    // 175. ON MESSAGE
    // ---------------------------
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLatestMessage(data);
      } catch (err) {
        console.error("Invalid JSON:", event.data);
      }
    };

    // ---------------------------
    // ON ERROR
    // ---------------------------
    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    // ---------------------------
    // 173. ON CLOSE (RECONNECT)
    // ---------------------------
    ws.onclose = () => {
      console.warn("⚠️ WebSocket disconnected");

      const delay = getBackoffDelay();
      reconnectAttempts.current += 1;

      setTimeout(() => {
        console.log(`🔄 Reconnecting in ${delay / 1000}s...`);
        connect();
      }, delay);
    };
  }, [url]);


  // --------------------------------------------------
  // INIT CONNECTION
  // --------------------------------------------------
  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);


  // --------------------------------------------------
  // SEND MESSAGE FUNCTION
  // --------------------------------------------------
  const sendMessage = (message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn("WebSocket not connected");
    }
  };

  return { latestMessage, sendMessage };
};