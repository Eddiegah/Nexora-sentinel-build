import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { logout } from "../lib/api";

export default function NavBar() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <nav
      style={{
        background: "#1a1d27",
        borderBottom: "1px solid #2a2d3a",
        padding: "0.75rem 1.5rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
      aria-label="Main navigation"
    >
      <button
        onClick={() => navigate("/")}
        style={{
          background: "none",
          color: "#38bdf8",
          fontWeight: 700,
          fontSize: "1.1rem",
          padding: 0,
          letterSpacing: "-0.01em",
        }}
        aria-label="Nexora Sentinel home"
      >
        ◎ Nexora Sentinel
      </button>

      <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
        {location.pathname !== "/" && (
          <button
            onClick={() => navigate("/")}
            style={{ background: "#2a2d3a", color: "#e2e8f0", fontSize: "0.85rem" }}
          >
            Dashboard
          </button>
        )}
        <button
          onClick={logout}
          style={{ background: "transparent", color: "#8892a4", fontSize: "0.85rem", border: "1px solid #2a2d3a" }}
        >
          Sign out
        </button>
      </div>
    </nav>
  );
}
