"use strict";
// Vehicle details payload collector
// This file is part of the fixed_assets module. Do not edit directly.

function collectVehicleDetailsPayload() {
  return {
    brand: document.getElementById("vd_brand")?.value || "",
    model: document.getElementById("vd_model")?.value || "",
    year: parseInt(document.getElementById("vd_year")?.value, 10) || null,
    vin: document.getElementById("vd_vin")?.value || "",
    engine: document.getElementById("vd_engine")?.value || "",
    transmission: document.getElementById("vd_transmission")?.value || "",
    fuel_type: document.getElementById("vd_fuel_type")?.value || "",
    mileage: parseFloat(document.getElementById("vd_mileage")?.value) || 0,
    plate_number: document.getElementById("vd_plate_number")?.value || "",
    license_expiry_date: document.getElementById("vd_license_expiry_date")?.value || null,
    color: document.getElementById("vd_color")?.value || "",
  };
}

