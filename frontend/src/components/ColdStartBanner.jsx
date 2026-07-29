import React, { useEffect, useState } from "react";
import { checkHealth } from "../lib/api";

/**
 * Polls /health every 4 seconds while the backend is waking up from
 * Render's free-tier 15-minute sleep.  Hides itself once the server responds.
 */
export default function ColdStartBanner({ onReady }) {
  const [waking, setWaking] = useState(false);
  const [dots, setDots] = useState(".");

  useEffect(() => {
    let cancelled = false;
    let dotInterval;

    async function probe() {
      try {
        await checkHealth();
        if (!cancelled) {
          setWaking(false);
          onReady?.();
        }
      } catch {
        if (!cancelled) {
          setWaking(true);
          // Animate dots while waiting
          dotInterval = setInterval(() => {
            setDots((d) => (d.length >= 3 ? "." : d + "."));
          }, 600);
          setTimeout(() => {
            clearInterval(dotInterval);
            if (!cancelled) probe();
          }, 4000);
        }
      }
    }

    probe();
    return () => {
      cancelled = true;
      clearInterval(dotInterval);
    };
  }, [onReady]);

  if (!waking) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: 8,
        padding: "0.75rem 1.25rem",
        marginBottom: "1rem",
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        fontSize: "0.875rem",
        color: "#94a3b8",
      }}
    >
      <span style={{ fontSize: "1.1rem" }}>⏳</span>
      <span>
        <strong style={{ color: "#e2e8f0" }}>Waking up the server{dots}</strong>
        <br />
        The backend is starting after being idle. This takes about 60 seconds on
        the free tier.
      </span>
    </div>
  );
}
