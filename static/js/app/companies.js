"use strict";

window.getCompanies = () => _companies;
window.refreshCompanies = async () => {
  const r = await fetch("/api/companies/");
  _companies = (await r.json()).companies || [];
};
