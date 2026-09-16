"use strict";
// Gold unit-conversion and purity-normalization helpers.
// Part of the fixed_assets module (split from the former monolithic gold.js,
// 200-line rule). Do not edit directly.

function getGoldUnitFactor(unitValue) {
  const normalized = String(unitValue || "gram")
    .trim()
    .toLowerCase();
  const map = {
    g: 1,
    gm: 1,
    gram: 1,
    grams: 1,
    kg: 1000,
    kilogram: 1000,
    kilograms: 1000,
    oz: 31.1034768,
    ounce: 31.1034768,
    ounces: 31.1034768,
    tola: 11.6638038,
  };
  return map[normalized] || 1;
}

function normalizeGoldPurity(purityValue) {
  const text = String(purityValue || "")
    .trim()
    .toLowerCase();
  if (text.includes("24") || text.includes("999")) return "24k";
  if (text.includes("22") || text.includes("916")) return "22k";
  if (text.includes("21") || text.includes("875")) return "21k";
  if (text.includes("18") || text.includes("750")) return "18k";
  return "24k";
}
