"use strict";

window.getBanks = () => _banks;
window.refreshBanks = async () => {
  const r = await fetch("/api/banks/");
  _banks = (await r.json()).banks || [];
};
