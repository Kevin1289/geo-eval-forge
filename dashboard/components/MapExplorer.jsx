"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";

const OSM_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

function colorFor(props) {
  if (props._role === "target") return "#58a6ff";
  if (props.within === false) return "#8b949e";
  if (typeof props._role === "string" && props._role.startsWith("wrong")) return "#f85149";
  return "#3fb950";
}

export default function MapExplorer({ mapPath }) {
  const ref = useRef(null);

  useEffect(() => {
    let map;
    let cancelled = false;

    fetch(mapPath)
      .then((r) => r.json())
      .then((fc) => {
        if (cancelled || !ref.current) return;

        // bounds + per-feature color
        const b = new maplibregl.LngLatBounds();
        for (const f of fc.features) {
          f.properties = f.properties || {};
          f.properties._color = colorFor(f.properties);
          const g = f.geometry;
          if (g.type === "Point") b.extend(g.coordinates);
          else if (g.type === "Polygon") g.coordinates[0].forEach((c) => b.extend(c));
        }

        map = new maplibregl.Map({
          container: ref.current,
          style: OSM_STYLE,
          bounds: b,
          fitBoundsOptions: { padding: 60, maxZoom: 15 },
        });
        map.addControl(new maplibregl.NavigationControl(), "top-right");

        map.on("load", () => {
          map.addSource("data", { type: "geojson", data: fc });
          map.addLayer({
            id: "polys-fill", type: "fill", source: "data",
            filter: ["==", ["geometry-type"], "Polygon"],
            paint: { "fill-color": "#58a6ff", "fill-opacity": 0.08 },
          });
          map.addLayer({
            id: "polys-line", type: "line", source: "data",
            filter: ["==", ["geometry-type"], "Polygon"],
            paint: { "line-color": "#58a6ff", "line-width": 1.5 },
          });
          map.addLayer({
            id: "pts", type: "circle", source: "data",
            filter: ["==", ["geometry-type"], "Point"],
            paint: {
              "circle-radius": ["case", ["==", ["get", "_role"], "target"], 8, 6],
              "circle-color": ["get", "_color"],
              "circle-stroke-width": 1.5,
              "circle-stroke-color": "#0d1117",
            },
          });

          const popup = new maplibregl.Popup({ closeButton: false });
          map.on("mousemove", "pts", (e) => {
            const p = e.features[0].properties;
            const txt = Object.entries(p)
              .filter(([k]) => !k.startsWith("_color"))
              .map(([k, v]) => `${k}: ${v}`)
              .join("<br/>");
            popup.setLngLat(e.lngLat).setHTML(txt).addTo(map);
            map.getCanvas().style.cursor = "pointer";
          });
          map.on("mouseleave", "pts", () => {
            popup.remove();
            map.getCanvas().style.cursor = "";
          });
        });
      })
      .catch(() => {});

    return () => {
      cancelled = true;
      if (map) map.remove();
    };
  }, [mapPath]);

  return (
    <div>
      <div className="maplibre-map" ref={ref} />
      <div className="legend">
        <span><i style={{ background: "#3fb950" }} />golden / correct</span>
        <span><i style={{ background: "#f85149" }} />wrong candidate</span>
        <span><i style={{ background: "#8b949e" }} />outside / not-within</span>
        <span><i style={{ background: "#58a6ff" }} />target</span>
      </div>
    </div>
  );
}
