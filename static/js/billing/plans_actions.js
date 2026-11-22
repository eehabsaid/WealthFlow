// Customer-facing plans page actions: upgrade request and checkout (loaded after plans_page.js).

async function submitUpgradeRequest(planId) {
  try {
    const res = await fetch("/api/billing/upgrade-request/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        plan_id: planId,
        currency_code: _plansPageCurrency,
      }),
    });
    if (!res.ok) throw new Error("failed");
    showToast(t("upgrade_request_sent", "Upgrade request sent ✓"), "success");
    renderBillingPlansPage();
    if (typeof checkBillingStatus === "function") checkBillingStatus();
  } catch (e) {
    showToast(
      t("error_sending_upgrade_request", "Couldn't send your request. Please try again."),
      "error"
    );
  }
}

async function checkoutPlan(planId) {
  try {
    const res = await fetch("/api/billing/checkout/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        plan_id: planId,
        currency_code: _plansPageCurrency,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      const err = new Error(data.error || "checkout failed");
      // 400 carries a customer-safe reason (e.g. currency not payable online yet).
      err.serverMessage = res.status === 400 && !!data.error;
      throw err;
    }

    if (data.mode === "paymob") {
      window.location.href = data.iframe_url;
      return;
    }

    // No gateway configured yet — fake/test-mode checkout.
    if (
      !confirm(
        t(
          "fake_payment_confirm",
          "Test Payment Mode: no payment gateway is configured yet. Simulate a successful payment now?"
        )
      )
    ) {
      return;
    }

    const completeRes = await fetch("/api/billing/checkout/fake-complete/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ invoice_id: data.invoice_id }),
    });
    if (!completeRes.ok) throw new Error("fake payment failed");

    showToast(
      t("fake_payment_success", "Test payment complete ✓ — you're now on this plan."),
      "success"
    );
    renderBillingPlansPage();
    if (typeof checkBillingStatus === "function") checkBillingStatus();
    if (typeof renderSidebar === "function") renderSidebar();
  } catch (e) {
    const isServerMessage = e && e.serverMessage;
    showToast(
      isServerMessage
        ? e.message
        : t("error_starting_checkout", "Couldn't start checkout. Please try again."),
      "error"
    );
  }
}

window.submitUpgradeRequest = submitUpgradeRequest;
window.checkoutPlan = checkoutPlan;
