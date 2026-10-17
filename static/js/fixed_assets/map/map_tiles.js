"use strict";
// Map background tiles for every Leaflet map (property editor + asset view).
// The tile server is a setting (Settings > Property Valuation > Map background), so a provider that starts
// requiring a key can be swapped from the UI without a code change. The default is the free OpenStreetMap server.

const DEFAULT_MAP_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const DEFAULT_MAP_TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

let mapTileConfigPromise = null;

function resetMapTileConfig() {
  mapTileConfigPromise = null;
}

function loadMapTileConfig() {
  if (!mapTileConfigPromise) {
    mapTileConfigPromise = fetch("/api/settings/")
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => {
        const s = (data && data.settings) || {};
        return {
          url: String(s.map_tile_url || "").trim() || DEFAULT_MAP_TILE_URL,
          attribution: String(s.map_tile_attribution || "").trim() || DEFAULT_MAP_TILE_ATTRIBUTION,
        };
      })
      .catch(() => ({ url: DEFAULT_MAP_TILE_URL, attribution: DEFAULT_MAP_TILE_ATTRIBUTION }));
  }
  return mapTileConfigPromise;
}

// Adds the configured background to `map` as soon as the setting is known; a map removed meanwhile is left alone.
async function addMapTiles(map) {
  const cfg = await loadMapTileConfig();
  try {
    // The site sends "Referrer-Policy: same-origin", so tile servers would get no Referer and OpenStreetMap answers
    // "Access blocked" (403). Tiles alone are sent the origin (https://host, no path); the rest of the app is unchanged.
    L.tileLayer(cfg.url, {
      attribution: cfg.attribution,
      maxZoom: 19,
      referrerPolicy: "origin",
    }).addTo(map);
  } catch (err) {
    // The map was closed before the setting arrived: nothing to draw on.
  }
}
