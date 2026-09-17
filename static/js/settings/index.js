"use strict";
// Settings entry-point and router
// This file is part of the settings module. Do not edit directly.

async function renderSettings(route) {
  const mc = document.getElementById("main-content");

  const TAB_MAP = {
    companies: "companies",
    banks: "banks",
    currency: "currency",
    users: "users",
    billing: "billing",
    emailtemplates: "emailtemplates",
    translationcoverage: "translationcoverage",
    translations: "translations",
    reminders: "reminders",
    certstatus: "certstatus",
    goldsettings: "goldsettings",
    propertyvaluation: "propertyvaluation",
    "settings-dashboard": "dashboard",
    languages: "languages",
    backuprestore: "backuprestore",
    documentation: "documentation",
    aiadvisor: "aiadvisor",
    roles: "roles",
  };

  let activeTab = "languages";
  for (const [key, val] of Object.entries(TAB_MAP)) {
    if (route.includes(key)) {
      activeTab = val;
      break;
    }
  }

  const tabs = [
    { id: "languages", i18n: "settings_languages", fallback: "Languages", route: "settings-languages", key: "settings_languages" },
    { id: "companies", i18n: "settings_companies", fallback: "Companies", route: "settings-companies", key: "settings_companies" },
    { id: "banks", i18n: "settings_banks", fallback: "Banks", route: "settings-banks", key: "settings_banks" },
    { id: "currency", i18n: "settings_currency", fallback: "Currency", route: "settings-currency", key: "settings_currency" },
    { id: "users", i18n: "settings_users", fallback: "Users", route: "settings-users", key: "settings_users" },
    { id: "roles", i18n: "settings_roles", fallback: "Roles", route: "settings-roles", key: "settings_roles" },
    { id: "billing", i18n: "settings_billing", fallback: "Billing Plans", route: "settings-billing", key: "settings_billing" },
    { id: "emailtemplates", i18n: "settings_email_templates", fallback: "Email Templates", route: "settings-emailtemplates", key: "settings_emailtemplates" },
    { id: "translations", i18n: "settings_translations", fallback: "Translations", route: "settings-translations", key: "settings_translations" },
    { id: "translationcoverage", i18n: "settings_translation_coverage", fallback: "Translation Coverage", route: "settings-translationcoverage", key: "settings_translationcoverage" },
    { id: "reminders", i18n: "tab_reminders", fallback: "Reminders", route: "settings-reminders", key: "settings_reminders" },
    { id: "certstatus", i18n: "tab_cert_status", fallback: "Certificate Status", route: "settings-certstatus", key: "settings_certstatus" },
    { id: "goldsettings", i18n: "tab_gold_settings", fallback: "Gold Settings", route: "settings-goldsettings", key: "settings_goldsettings" },
    { id: "propertyvaluation", i18n: "tab_property_valuation", fallback: "Property Valuation Settings", route: "settings-propertyvaluation", key: "settings_propertyvaluation" },
    { id: "dashboard", i18n: "tab_dashboard_sett", fallback: "Dashboard", route: "settings-dashboard", key: "settings_dashboard" },
    { id: "backuprestore", i18n: "settings_backup_restore", fallback: "Backup & Restore", route: "settings-backuprestore", key: "settings_backuprestore" },
    { id: "documentation", i18n: "settings_documentation", fallback: "Documentation", route: "settings-documentation", key: "settings_documentation" },
    { id: "aiadvisor", i18n: "settings_ai_advisor", fallback: "AI Advisor", route: "settings-aiadvisor", key: "settings_aiadvisor" },
  ];

  const visibleTabs = tabs.filter((tab) => hasPermission(tab.key));
  if (!visibleTabs.some((tab) => tab.id === activeTab)) {
    activeTab = visibleTabs.length ? visibleTabs[0].id : "languages";
  }

  const tabBar = visibleTabs
    .map((tab) => {
      const label = t(tab.i18n, tab.fallback || tab.id);
      return `
        <button class="wf-tab ${activeTab === tab.id ? "active" : ""}"
            onclick="navigate('${tab.route}')"
            data-i18n="${tab.i18n}">
            ${label}
        </button>`;
    })
    .join("");

  const activeTabObj = visibleTabs.find((tab) => tab.id === activeTab) || visibleTabs[0];
  if (!activeTabObj) {
    mc.innerHTML = "";
    return;
  }
  const activeTabLabel = t(activeTabObj.i18n, activeTabObj.fallback || activeTabObj.id);

  mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title" data-i18n="${activeTabObj.i18n}">${activeTabLabel}</div></div>
        </div>
        <div class="wf-tabs-shell">
          <div class="wf-tabs-row" id="settingsTabsBar" role="tablist">
              ${tabBar}
          </div>
        </div>
        <div id="settingsContent"></div>`;

  applyTranslations();
  if (typeof window.initTabsWithMoreMenu === "function") {
    window.initTabsWithMoreMenu({
      containerId: "settingsTabsBar",
      visibleCount: 4,
      moreLabel: t("financial_advisor_tab_more", "More"),
      tabSelector: ".wf-tab",
      activeClass: "active",
    });
  }

  const renderers = {
    languages: renderLanguageSettings,
    companies: renderCompanySettings,
    currency: renderCurrencySettings,
    users: renderUserSettings,
    roles: renderRoleSettings,
    emailtemplates: renderEmailTemplateSettings,
    translations: renderTranslationSettings,
    translationcoverage: renderTranslationCoverage,
    reminders: renderReminderSettings,
    certstatus: renderCertStatusSettings,
    goldsettings: renderGoldSettings,
    propertyvaluation: renderPropertyValuationSettings,
    dashboard: renderDashboardSettings,
    banks: renderBankSettings,
    backuprestore: renderBackupRestoreSettings,
    documentation: renderDocumentationSettings,
    aiadvisor: renderAIAdvisorSettings,
    billing: renderBillingSettings,
  };

  await (renderers[activeTab] || renderers.banks)();
}
