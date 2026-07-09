"use strict";
// Other asset details payload collector
// This file is part of the fixed_assets module. Do not edit directly.

function collectOtherAssetDetailsPayload() {
  return {
    category: document.getElementById("od_category")?.value || "",
    manufacturer: document.getElementById("od_manufacturer")?.value || "",
    model: document.getElementById("od_model")?.value || "",
    serial_number: document.getElementById("od_serial_number")?.value || "",
    description: document.getElementById("od_description")?.value || "",
    warranty_expiry: document.getElementById("od_warranty_expiry")?.value || null,
    notes: document.getElementById("od_notes")?.value || "",
  };
}

