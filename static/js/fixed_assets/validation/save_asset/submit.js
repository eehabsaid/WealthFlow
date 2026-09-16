"use strict";
// Submits the fixed-asset save payload and parses server error responses.
// Part of the fixed_assets module (split from the former monolithic
// save_asset.js, 200-line rule). Do not edit directly.

async function submitFixedAssetPayload(url, method, payload) {
  const response = await fetch(url, {
    method: method,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = t("error_saving_fixed_asset", "Error saving fixed asset");
    try {
      const errorPayload = await response.json();
      if (errorPayload?.error_key) {
        message = t(errorPayload.error_key, errorPayload.error || message);
      } else if (errorPayload?.error) {
        message = errorPayload.error;
      }
    } catch (_) {
      // Keep fallback message.
    }
    throw new Error(message);
  }

  return await response.json();
}
