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
  };

  let activeTab = "languages";
  for (const [key, val] of Object.entries(TAB_MAP)) {
    if (route.includes(key)) {
      activeTab = val;
      break;
    }
  }

  const tabs = [
    {
      id: "languages",
      i18n: "settings_languages",
      fallback: "Languages",
      route: "settings-languages",
    },
    {
      id: "companies",
      i18n: "settings_companies",
      fallback: "Companies",
      route: "settings-companies",
    },
    { id: "banks", i18n: "settings_banks", fallback: "Banks", route: "settings-banks" },
    { id: "currency", i18n: "settings_currency", fallback: "Currency", route: "settings-currency" },
    { id: "users", i18n: "settings_users", fallback: "Users", route: "settings-users" },
    {
      id: "emailtemplates",
      i18n: "settings_email_templates",
      fallback: "Email Templates",
      route: "settings-emailtemplates",
    },
    {
      id: "translations",
      i18n: "settings_translations",
      fallback: "Translations",
      route: "settings-translations",
    },
    {
      id: "translationcoverage",
      i18n: "settings_translation_coverage",
      fallback: "Translation Coverage",
      route: "settings-translationcoverage",
    },
    { id: "reminders", i18n: "tab_reminders", fallback: "Reminders", route: "settings-reminders" },
    {
      id: "certstatus",
      i18n: "tab_cert_status",
      fallback: "Certificate Status",
      route: "settings-certstatus",
    },
    {
      id: "goldsettings",
      i18n: "tab_gold_settings",
      fallback: "Gold Settings",
      route: "settings-goldsettings",
    },
    {
      id: "propertyvaluation",
      i18n: "tab_property_valuation",
      fallback: "Property Valuation Settings",
      route: "settings-propertyvaluation",
    },
    {
      id: "dashboard",
      i18n: "tab_dashboard_sett",
      fallback: "Dashboard",
      route: "settings-dashboard",
    },
    {
      id: "backuprestore",
      i18n: "settings_backup_restore",
      fallback: "Backup & Restore",
      route: "settings-backuprestore",
    },
    {
      id: "documentation",
      i18n: "settings_documentation",
      fallback: "Documentation",
      route: "settings-documentation",
    },
    {
      id: "aiadvisor",
      i18n: "settings_ai_advisor",
      fallback: "AI Advisor",
      route: "settings-aiadvisor",
    },
  ];

  const tabBar = tabs
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

  const activeTabObj = tabs.find((tab) => tab.id === activeTab) || tabs[0];
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
  };

  await (renderers[activeTab] || renderers.banks)();
}

// ════════════════════════════════════════════════════════════════════════════
// DASHBOARD SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════

// ════════════════════════════════════════════════════════════════════════════
// GLOBAL WINDOW EXPORTS FOR HTML BACKWARD COMPATIBILITY
// ════════════════════════════════════════════════════════════════════════════

window.renderSettings = renderSettings;
window.renderDashboardSettings = renderDashboardSettings;
window.applySmtpPreset = applySmtpPreset;
window.saveSmtpSettingsFromGui = saveSmtpSettingsFromGui;
window.testSmtpSettingsFromGui = testSmtpSettingsFromGui;
window.saveAppSetting = saveAppSetting;
window.renderEmailTemplateSettings = renderEmailTemplateSettings;
window.showEmailTemplateModal = showEmailTemplateModal;
window.saveEmailTemplate = saveEmailTemplate;
window.renderGoldSettings = renderGoldSettings;
window.showGoldTypeModal = showGoldTypeModal;
window.renderPropertyValuationSettings = renderPropertyValuationSettings;
window.savePropertyValuationSettings = savePropertyValuationSettings;
window.scrapePropertyRates = scrapePropertyRates;
window.saveGoldType = saveGoldType;
window.disableGoldType = disableGoldType;
window.showGoldPurityModal = showGoldPurityModal;
window.saveGoldPurity = saveGoldPurity;
window.disableGoldPurity = disableGoldPurity;
window.renderLanguageSettings = renderLanguageSettings;
window.showAddLangModal = showAddLangModal;
window.showLanguageModal = showLanguageModal;
window.setActiveLang = setActiveLang;
window.saveLanguageUpdate = saveLanguageUpdate;
window.deleteLang = deleteLang;
window.saveNewLang = saveNewLang;
window.renderCurrencySettings = renderCurrencySettings;
window.showCurrencyModal = showCurrencyModal;
window.saveCurrency = saveCurrency;
window.deleteCurrency = deleteCurrency;
window.renderCompanySettings = renderCompanySettings;
window.showCompanyModal = showCompanyModal;
window.updateCompanyColor = updateCompanyColor;
window.saveCompany = saveCompany;
window.deleteCompany = deleteCompany;
window.renderBankSettings = renderBankSettings;
window.showBankModal = showBankModal;
window.saveBank = saveBank;
window.deleteBank = deleteBank;
window.renderUserSettings = renderUserSettings;
window.loadUsers = loadUsers;
window.showUserModal = showUserModal;
window.showPermissionsModal = showPermissionsModal;
window.handleUserSearch = handleUserSearch;
window.toggleSelectAll = toggleSelectAll;
window.getSelectedUserIds = getSelectedUserIds;
window.applyBulkAction = applyBulkAction;
window.saveUser = saveUser;
window.deleteUser = deleteUser;
window.addPermission = addPermission;
window.deletePermission = deletePermission;
window.renderTranslationSettings = renderTranslationSettings;
window.saveTranslations = saveTranslations;
window.filterTranslations = filterTranslations;
window.renderTranslationCoverage = renderTranslationCoverage;
window.showMissingTranslationsReport = showMissingTranslationsReport;
window.renderBackupRestoreSettings = renderBackupRestoreSettings;
window.triggerDownloadBackup = triggerDownloadBackup;
window.triggerUploadRestore = triggerUploadRestore;
window.createServerBackup = createServerBackup;
window.restoreServerBackup = restoreServerBackup;
window.deleteServerBackup = deleteServerBackup;
