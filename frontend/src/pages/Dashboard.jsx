import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { getRegions, getLatestPrediction } from "../lib/api";
import RiskMap from "../components/RiskMap";
import ColdStartBanner from "../components/ColdStartBanner";

export default function Dashboard() {
  const navigate = useNavigate();
  const [regions, setRegions] = useState([]);
  const [predictions, setPredictions] = useState(new Map()); // regionId → prediction
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortKey, setSortKey] = useState("score");
  const [sortAsc, setSortAsc] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const regionList = await getRegions();
      setRegions(regionList);

      // Fetch latest prediction for each region in parallel
      const results = await Promise.allSettled(
        regionList.map((r) => getLatestPrediction(r.id))
      );
      const predMap = new Map();
      results.forEach((result, idx) => {
        if (result.status === "fulfilled" && result.value) {
          predMap.set(regionList[idx].id, result.value);
        }
      });
      setPredictions(predMap);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function toggleSort(key) {
    if (sortKey === key) setSortAsc((a) => !a);
    else {
      setSortKey(key);
      setSortAsc(false);
    }
  }

  const sortedRows = useMemo(() => {
    return [...regions].sort((a, b) => {
      let va, vb;
      if (sortKey === "score") {
        va = predictions.get(a.id)?.risk_score ?? -1;
        vb = predictions.get(b.id)?.risk_score ?? -1;
      } else if (sortKey === "category") {
        const order = { high: 2, medium: 1, low: 0 };
        va = order[predictions.get(a.id)?.risk_category ?? "low"] ?? 0;
        vb = order[predictions.get(b.id)?.risk_category ?? "low"] ?? 0;
      } else {
        va = (a[sortKey] ?? "").toString().toLowerCase();
        vb = (b[sortKey] ?? "").toString().toLowerCase();
      }
      if (va < vb) return sortAsc ? -1 : 1;
      if (va > vb) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [regions, predictions, sortKey, sortAsc]);

  function SortHeader({ label, k }) {
    const active = sortKey === k;
    return (
      <th
        onClick={() => toggleSort(k)}
        style={{ cursor: "pointer", userSelect: "none", whiteSpace: "nowrap", padding: "0.6rem 0.5rem" }}
        aria-sort={active ? (sortAsc ? "ascending" : "descending") : "none"}
      >
        {label} {active ? (sortAsc ? "▲" : "▼") : <span style={{ color: "#3a3f52" }}>⇅</span>}
      </th>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "1.5rem 1rem" }}>
      {/* Page heading */}
      <div style={{ marginBottom: "1.25rem" }}>
        <h1 style={{ fontSize: "1.2rem", fontWeight: 600, color: "#e2e8f0" }}>
          Regional Risk Overview
        </h1>
        <p style={{ color: "#8892a4", fontSize: "0.85rem", marginTop: "0.2rem" }}>
          Malaria outbreak risk — Africa · {regions.length} regions tracked
        </p>
      </div>

      {/* Cold-start banner — polls /health until backend is awake */}
      <ColdStartBanner onReady={loadData} />

      {loading && (
        <p style={{ color: "#8892a4", marginBottom: "1rem" }}>Loading regions…</p>
      )}
      {error && (
        <p role="alert" style={{ color: "#ef4444", marginBottom: "1rem" }}>
          {error} —{" "}
          <button
            onClick={loadData}
            style={{ background: "none", color: "#38bdf8", padding: 0, fontSize: "0.9rem" }}
          >
            retry
          </button>
        </p>
      )}

      {/* Map */}
      {!loading && (
        <div className="card" style={{ marginBottom: "1.25rem", padding: 0, overflow: "hidden" }}>
          <RiskMap
            regions={regions}
            predictions={predictions}
            onRegionClick={(id) => navigate(`/regions/${id}`)}
          />
        </div>
      )}

      {/* Sortable table */}
      {!loading && regions.length > 0 && (
        <div className="card" style={{ overflowX: "auto" }}>
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}
            aria-label="Regional malaria risk table"
          >
            <thead>
              <tr style={{ borderBottom: "1px solid #2a2d3a", color: "#8892a4", textAlign: "left" }}>
                <SortHeader label="Region" k="name" />
                <SortHeader label="Country" k="country" />
                <SortHeader label="Risk Score" k="score" />
                <SortHeader label="Category" k="category" />
                <th style={{ padding: "0.6rem 0.5rem" }}>Details</th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((region) => {
                const pred = predictions.get(region.id);
                const cat = pred?.risk_category ?? null;
                const score = pred?.risk_score;
                return (
                  <tr
                    key={region.id}
                    style={{ borderBottom: "1px solid #1e2130", cursor: "pointer" }}
                    onClick={() => navigate(`/regions/${region.id}`)}
                  >
                    <td style={{ padding: "0.7rem 0.5rem", fontWeight: 500 }}>
                      {region.name}
                    </td>
                    <td style={{ padding: "0.7rem 0.5rem", color: "#8892a4" }}>
                      {region.country}
                    </td>
                    <td style={{ padding: "0.7rem 0.5rem" }}>
                      {score != null ? (
                        <span style={{ fontVariantNumeric: "tabular-nums" }}>
                          {(score * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span style={{ color: "#3a3f52" }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: "0.7rem 0.5rem" }}>
                      {cat ? (
                        <span className={`badge badge-${cat}`}>{cat}</span>
                      ) : (
                        <span style={{ color: "#3a3f52", fontSize: "0.8rem" }}>No data yet</span>
                      )}
                    </td>
                    <td style={{ padding: "0.7rem 0.5rem" }}>
                      <span style={{ color: "#38bdf8", fontSize: "0.85rem" }}>View →</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {!loading && regions.length === 0 && !error && (
        <div className="card" style={{ color: "#8892a4", textAlign: "center", padding: "2rem" }}>
          No regions found. Run the database migrations to seed the initial regions.
        </div>
      )}
    </div>
  );
}
