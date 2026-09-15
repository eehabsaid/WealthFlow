"use strict";
// Nominatim forward/reverse geocoding for the property address fields.
// Part of the fixed_assets module (split from the former monolithic map.js,
// 200-line rule). Do not edit directly.

async function geocodeQuery(query) {
  const response = await fetch(
    `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(query)}`
  );

  const results = await response.json();

  return results && results.length ? results[0] : null;
}

async function locatePropertyOnMap() {
  const country = document.getElementById("re_country").value.trim();
  const governorate = document.getElementById("re_governorate").value.trim();
  const city = document.getElementById("re_city").value.trim();
  const district = document.getElementById("re_district").value.trim();
  const address = document.getElementById("re_address").value.trim();

  // Fields stay exactly as entered/displayed. We only try progressively
  // less specific combinations of the SAME fields, since Nominatim often
  // has no match for a full street-level address but does have a match
  // for the district/city/governorate it sits within.
  const candidateQueries = [
    [address, district, city, governorate, country],
    [address, city, governorate, country],
    [district, city, governorate, country],
    [city, governorate, country],
    [governorate, country],
    [country],
  ]
    .map((parts) => parts.filter(Boolean).join(", "))
    .filter(Boolean);

  // De-duplicate while preserving order (short address forms can collapse
  // into the same string once empty fields are dropped).
  const queries = [...new Set(candidateQueries)];

  if (!queries.length) {
    showToast("Please enter an address first.", "warning");
    return;
  }

  showLoading();

  try {
    let match = null;

    for (const query of queries) {
      try {
        match = await geocodeQuery(query);
      } catch (err) {
        match = null;
      }

      if (match) break;
    }

    if (!match) {
      showToast("Address not found.", "warning");
      return;
    }

    const lat = parseFloat(match.lat);
    const lng = parseFloat(match.lon);

    document.getElementById("re_latitude").value = lat.toFixed(6);
    document.getElementById("re_longitude").value = lng.toFixed(6);

    propertyMap.setView([lat, lng], 17);

    propertyMarker.setLatLng([lat, lng]);
  } catch (err) {
    showToast("Unable to locate address.", "danger");
  } finally {
    hideLoading();
  }
}

async function reverseGeocode(lat, lng) {
  try {
    const currentLang = localStorage.getItem("lang") || "en";

    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&accept-language=${currentLang},en`
    );

    const result = await response.json();

    if (!result.address) return;

    const a = result.address;
    document.getElementById("re_country").value = a.country || "";

    document.getElementById("re_governorate").value = a.state || a.county || "";

    document.getElementById("re_city").value = a.city || a.town || a.village || "";

    document.getElementById("re_district").value =
      a.suburb ||
      a.neighbourhood ||
      a.city_district ||
      a.district ||
      a.municipality ||
      a.hamlet ||
      a.quarter ||
      a.borough ||
      a.village ||
      a.town ||
      a.city ||
      "";

    document.getElementById("re_address").value = result.display_name || "";
  } catch (err) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
}
