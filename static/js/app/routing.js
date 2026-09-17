"use strict";

function routeAllowed(hash) {
  if (isPrivilegedUser()) {
    return true;
  }
  if (hash === "billing-plans") {
    // Every account can view/upgrade their own plan, regardless of assigned page permissions.
    return true;
  }
  if (hash === "welcome") {
    return shouldShowWelcomeOnly();
  }
  if (hash === "dashboard") {
    return canAccessAny(["dashboard"]);
  }
  if (hash === "ai" || hash === "wealthflow-ai" || hash.startsWith("ai")) {
    return canAccessAny(["ai", "wealthflow_ai", "financial_advisor"]) && planAllowsAIWorkspace();
  }
  if (hash === "financial-advisor" || hash.startsWith("financial-advisor")) {
    return canAccessAny(["financial_advisor"]);
  }
  if (hash === "balance") {
    return canAccessAny(["balance", "banks"]);
  }
  if (hash === "bank-certificates") {
    return canAccessAny(["bank_certificates"]);
  }
  if (hash === "fixed-assets") {
    return canAccessAny(["fixed_assets"]);
  }
  if (
    hash === "employment" ||
    hash === "salary" ||
    hash.startsWith("employment-") ||
    hash.startsWith("salary-")
  ) {
    return canAccessAny(["employment", "salary", "companies", "all_companies"]);
  }
  if (hash === "exchange-rates") {
    return canAccessAny(["exchange_rates", "currencies"]);
  }
  if (hash === "gold-price") {
    return canAccessAny(["gold_price"]);
  }
  if (hash === "expenses") {
    return canAccessAny(["expenses"]);
  }
  if (hash === "expense-categories") {
    return canAccessAny(["expense-categories"]);
  }
  if (hash === "reports") {
    return canAccessAny(["reports"]);
  }
  if (hash === "advanced-reports") {
    return canAccessAny(["advanced_reports"]);
  }
  if (hash.startsWith("settings")) {
    if (isPrivilegedUser()) return true;
    return (_allowedPages || []).some((k) => k === "settings" || k.startsWith("settings_"));
  }
  return false;
}

function getFirstAllowedRoute() {
  if (isPrivilegedUser()) {
    return "dashboard";
  }

  // For normal users, homepage should be one of the assigned pages.
  for (const pageKey of _allowedPages || []) {
    const route = permissionToRoute(pageKey);
    if (route && routeAllowed(route)) {
      return route;
    }
  }

  const candidates = [
    "dashboard",
    "ai",
    "financial-advisor",
    "employment",
    "balance",
    "bank-certificates",
    "fixed-assets",
    "exchange-rates",
    "gold-price",
    "expenses",
    "expense-categories",
    "reports",
    "advanced-reports",
    "settings-languages",
  ];
  for (const candidate of candidates) {
    if (routeAllowed(candidate)) {
      return candidate;
    }
  }
  return "welcome";
}

function permissionToRoute(pageKey) {
  if (pageKey === "dashboard") return "dashboard";
  if (pageKey === "ai" || pageKey === "wealthflow_ai") return "ai";
  if (pageKey === "financial_advisor") return "financial-advisor";
  if (pageKey === "balance" || pageKey === "banks") return "balance";
  if (pageKey === "bank_certificates") return "bank-certificates";
  if (pageKey === "fixed_assets") return "fixed-assets";
  if (
    pageKey === "employment" ||
    pageKey === "salary" ||
    pageKey === "companies" ||
    pageKey === "all_companies"
  )
    return "employment";
  if (pageKey === "exchange_rates" || pageKey === "currencies") return "exchange-rates";
  if (pageKey === "gold_price") return "gold-price";
  if (pageKey === "expenses") return "expenses";
  if (pageKey === "expense-categories") return "expense-categories";
  if (pageKey === "reports") return "reports";
  if (pageKey === "advanced_reports") return "advanced-reports";
  if (pageKey === "settings") return "settings-languages";
  if (pageKey === "user_management") return "settings-users";
  if (typeof pageKey === "string" && pageKey.startsWith("settings_")) return "settings-languages";
  return "";
}
