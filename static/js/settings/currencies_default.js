// Currency configuration settings: multi-currency switch and default currency (loaded after currencies.js).

async function setMultiCurrencyEnabled(enabled) {
  const res = await fetch("/api/settings/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ settings: { multi_currency_enabled: enabled ? "true" : "false" } }),
  });
  if (res.ok) {
    showToast(
      enabled
        ? t("multi_currency_enabled_saved", "Users can now choose their own default currency ✓")
        : t(
            "multi_currency_disabled_saved",
            "Currency choice is now locked to the platform default ✓"
          )
    );
  } else {
    showToast(t("error_saving_settings", "Error saving setting"), "error");
    document.getElementById("multiCurrencyToggle").checked = !enabled;
  }
}

async function setDefaultCurrency(code) {
  const warning = t(
    "currency_default_confirm",
    "Changing your default currency recalculates all your totals in the new currency. Continue?"
  );
  if (!confirm(warning)) return;
  const res = await fetch("/api/base-currency/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  const body = await res.json().catch(() => ({}));
  if (res.ok) {
    showToast(t("currency_default_saved", "Default currency updated ✓"));
    window.location.reload();
  } else {
    showToast(t(body.error_key || "currency_default_invalid", body.error || "Error"), "error");
  }
}
