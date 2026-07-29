import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../lib/api";
import { useAuth } from "../hooks/useAuth";

export default function Login() {
  const navigate = useNavigate();
  const { saveToken } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await login(email, password);
      saveToken(data.access_token);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message ?? "Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1rem",
      }}
    >
      <div className="card" style={{ width: "100%", maxWidth: 380 }}>
        <h1
          style={{
            fontSize: "1.5rem",
            fontWeight: 700,
            marginBottom: "0.25rem",
            color: "#38bdf8",
          }}
        >
          Nexora Sentinel
        </h1>
        <p style={{ color: "#8892a4", marginBottom: "1.5rem", fontSize: "0.9rem" }}>
          Malaria outbreak risk intelligence for Africa
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="email" style={{ fontSize: "0.85rem", color: "#8892a4" }}>
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ marginTop: "0.3rem", marginBottom: "1rem" }}
          />

          <label htmlFor="password" style={{ fontSize: "0.85rem", color: "#8892a4" }}>
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ marginTop: "0.3rem", marginBottom: "1.25rem" }}
          />

          {error && (
            <p
              role="alert"
              style={{
                color: "#ef4444",
                fontSize: "0.85rem",
                marginBottom: "1rem",
              }}
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ width: "100%" }}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </main>
  );
}
