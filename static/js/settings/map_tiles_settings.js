"use strict";
// "Map background" block of the Property Valuation settings: which tile server draws the property maps.
// Empty fields mean the built-in free OpenStreetMap server. Used by property_valuation.js.

function mapTilesSettingsHtml(settings) {
  const url = (settings && settings.map_tile_url) || "";
  const attribution = (settings && settings.map_tile_attribution) || "";
  const defaultUrl = typeof DEFAULT_MAP_TILE_URL === "string" ? DEFAULT_MAP_TILE_URL : "";
  return `
    <div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border-color);">
      <div style="font-weight:700;margin-bottom:4px;" data-i18n="map_tiles_title">${t("map_tiles_title", "Map background")}</div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:10px;" data-i18n="map_tiles_hint">${t("map_tiles_hint", "Tile server used by the property maps. Leave empty for the free OpenStreetMap server. Use {z}, {x}, {y} (and {s} for subdomains) in the address.")}</div>
      <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="map_tiles_url_label">${t("map_tiles_url_label", "Tile server URL")}</label>
      <input id="mapTileUrl" class="form-control" type="text" value="${escapeHtml(url)}" placeholder="${escapeHtml(defaultUrl)}">
      <label style="display:block;margin-top:12px;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="map_tiles_attribution_label">${t("map_tiles_attribution_label", "Map credit text (HTML allowed)")}</label>
      <input id="mapTileAttribution" class="form-control" type="text" value="${escapeHtml(attribution)}">
      <button type="button" class="btn-secondary-custom" style="margin-top:10px;" onclick="resetMapTilesFields()" data-i18n="map_tiles_reset">${t("map_tiles_reset", "Use default map")}</button>
    </div>`;
}

function resetMapTilesFields() {
  document.getElementById("mapTileUrl").value = "";
  document.getElementById("mapTileAttribution").value = "";
}

// The two settings to save, or null (after a toast) when the address cannot work as a tile server.
function mapTilesSettingsValues() {
  const url = document.getElementById("mapTileUrl")?.value?.trim() || "";
  const attribution = document.getElementById("mapTileAttribution")?.value?.trim() || "";
  if (url && !(/^https?:\/\//i.test(url) && ["{z}", "{x}", "{y}"].every((p) => url.includes(p)))) {
    showToast(
      t(
        "invalid_map_tile_url",
        "The tile server URL must start with http(s):// and contain {z}, {x} and {y}."
      ),
      "error"
    );
    return null;
  }
  return [
    ["map_tile_url", url],
    ["map_tile_attribution", attribution],
  ];
}
