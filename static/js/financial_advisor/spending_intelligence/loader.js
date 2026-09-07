"use strict";
// Spending intelligence: state + loadSpendingIntelligence data fetch/dispatch.


let _spendingIntelligenceLoaded = false;
let _spendingIntelligenceData = null;

async function loadSpendingIntelligence(force = false) {
  if (_spendingIntelligenceData && !force) {
    _renderSpendingIntelligence(_spendingIntelligenceData);
    _spendingIntelligenceLoaded = true;
    return;
  }

  _renderSpendingIntelligenceLoading();
  try {
    const response = await fetch("/api/financial-advisor/spending-intelligence/");
    if (!response.ok) {
      throw new Error("spending_intelligence_fetch_failed");
    }
    const payload = await response.json();
    _spendingIntelligenceData = payload;
    _renderSpendingIntelligence(payload);
    _spendingIntelligenceLoaded = true;
  } catch (error) {
    _renderSpendingIntelligenceError();
  }
}

window.loadSpendingIntelligence = loadSpendingIntelligence;
