import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { getRegion, getLatestPrediction, getPredictionHistory } from "../lib/api";

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  Title, Tooltip, Legend, Filler
);

function ShapBar({ feature }) {
  const maxBar = 100;
  const pct = Math.min(Math.abs(feature.shap_value) * 300, maxBar); // scale for display
  const positive = feature.shap_value > 0;
  return (
    <li
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        padding: "0.45rem 0",
        borderBottom: "1px solid #1e2130",
      }}
    >
      <span style={{ flex: "0 0 200px", fontSize: "0.85rem" }}>{feature.label}</span>
      <span style={{ flex: "0 0 70px", fontSize: "0.8rem", color: "#8892a4", textAlign: "right" }}>
        {typeof feature.feature_value === "number"
          ? feature.feature_value.toFixed(1)
          : feature.feature_value ?? "—"}
      </span>
      <div style={{ flex: 1, background: "#1e2130", borderRadius: 4, height: 10, overflow: "hidden" }}>
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: positive ? "#ef4444" : "#22c55e",
            borderRadius: 4,
            transition: "width 0.4s ease",
          }}
          role="presentation"
        />
      </div>
      <span
        style={{
          flex: "0 0 55px",
          fontSize: "0.8rem",
          color: positive ? "#ef4444" : "#22c55e",
          textAlign: "right",
        }}
      >
        {positive ? "+" : ""}{feature.shap_value.toFixed(3)}
      </span>
    </li>
  );
}

export default function RegionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [region, setRegion] = useState(null);
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [regionData, latestData, historyData] = await Promise.all([
          getRegion(id),
          getLatestPrediction(id),
          getPredictionHistory(id),
        ]);
        setRegion(regionData);
        setLatest(latestData);
        setHistory(historyData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) {
    return (
      <div style={{ padding: "2rem", color: "#8892a4" }}>
        Loading region data…
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "2rem" }}>
        <p role="alert" style={{ color: "#ef4444", marginBottom: "1rem" }}>
          {error}
        </p>
        <button onClick={() => navigate(-1)} style={{ background: "#2a2d3a", color: "#e2e8f0" }}>
          ← Back
        </button>
      </div>
    );
  }

  const cat = latest?.risk_category ?? "low";
  const shap = latest?.shap_explanation;

  // Chart data
  const chartLabels = history.map((h) =>
    new Date(h.predicted_at).toLocaleDateString("en-GB", { month: "short", day: "numeric" })
  );
  const chartData = {
    labels: chartLabels,
    datasets: [
      {
        label: "Risk Score",
        data: history.map((h) => parseFloat((h.risk_score * 100).toFixed(1))),
        borderColor: "#38bdf8",
        backgroundColor: "rgba(56,189,248,0.12)",
        fill: true,
        tension: 0.3,
        pointRadius: 4,
      },
    ],
  };
  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: {
        display: true,
        text: "Risk Score History (%)",
        color: "#8892a4",
        font: { size: 13 },
      },
    },
    scales: {
      x: { ticks: { color: "#8892a4" }, grid: { color: "#1e2130" } },
      y: {
        min: 0,
        max: 100,
        ticks: { color: "#8892a4", callback: (v) => `${v}%` },
        grid: { color: "#1e2130" },
      },
    },
  };

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "1.5rem 1rem" }}>
      <button
        onClick={() => navigate(-1)}
        style={{ background: "#2a2d3a", color: "#e2e8f0", marginBottom: "1.25rem" }}
      >
        ← Back
      </button>

      {/* Header */}
      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2 style={{ fontSize: "1.3rem", fontWeight: 700 }}>
              {region ? `${region.name}, ${region.country}` : `Region #${id}`}
            </h2>
            <p style={{ color: "#8892a4", fontSize: "0.85rem", marginTop: "0.2rem" }}>
              {region
                ? `${region.latitude.toFixed(4)}°, ${region.longitude.toFixed(4)}° · Model: ${latest?.model_version ?? "—"}`
                : `Model version: ${latest?.model_version ?? "—"}`}
            </p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "2rem", fontWeight: 700 }}>
              {latest ? `${(latest.risk_score * 100).toFixed(1)}%` : "—"}
            </div>
            <span className={`badge badge-${cat}`}>{cat} risk</span>
          </div>
        </div>
      </div>

      {/* SHAP explanation */}
      {shap && (
        <div className="card" style={{ marginBottom: "1.25rem" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
            Why this score? (SHAP feature contributions)
          </h3>
          <p style={{ color: "#8892a4", fontSize: "0.8rem", marginBottom: "0.75rem" }}>
            Red bars push the risk score higher; green bars push it lower.
            Base value: {(shap.base_value * 100).toFixed(1)}%
          </p>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {shap.features.map((f) => (
              <ShapBar key={f.raw_name} feature={f} />
            ))}
          </ul>
        </div>
      )}

      {/* History chart */}
      {history.length > 1 ? (
        <div className="card">
          <Line data={chartData} options={chartOptions} aria-label="Risk score history chart" />
        </div>
      ) : (
        <div className="card" style={{ color: "#8892a4", fontSize: "0.9rem" }}>
          Not enough historical predictions yet to show a trend chart.
          Predictions accumulate each time the ingestion job runs.
        </div>
      )}
    </div>
  );
}
