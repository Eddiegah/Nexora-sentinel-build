import React, { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";

const RISK_COLORS = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#ef4444",
};

/**
 * RiskMap — renders an OpenStreetMap tile layer with colored circle markers
 * for each region, sized and colored by risk category.
 *
 * Props:
 *   regions: Array<{ id, name, country, latitude, longitude }>
 *   predictions: Map<regionId, { risk_score, risk_category }>
 *   onRegionClick: (regionId) => void
 */
export default function RiskMap({ regions = [], predictions = new Map(), onRegionClick }) {
  return (
    <MapContainer
      center={[2, 20]}   // Centered on sub-Saharan Africa
      zoom={4}
      style={{ height: "420px", width: "100%", borderRadius: 8 }}
      aria-label="Malaria risk map of Africa"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {regions.map((region) => {
        const pred = predictions.get(region.id);
        const category = pred?.risk_category ?? "low";
        const score = pred?.risk_score ?? 0;
        const color = RISK_COLORS[category] ?? RISK_COLORS.low;

        return (
          <CircleMarker
            key={region.id}
            center={[region.latitude, region.longitude]}
            radius={12 + score * 10}
            pathOptions={{
              color,
              fillColor: color,
              fillOpacity: 0.75,
              weight: 2,
            }}
            eventHandlers={{
              click: () => onRegionClick?.(region.id),
            }}
            aria-label={`${region.name}: ${category} risk`}
          >
            <Tooltip>
              <strong>{region.name}</strong>, {region.country}
              <br />
              Risk: <em>{category}</em> ({(score * 100).toFixed(1)}%)
            </Tooltip>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
