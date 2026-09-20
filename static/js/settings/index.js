"use strict";
// Settings entry-point and router
// This file is part of the settings module. Do not edit directly.

async function renderSettings(route) {
  const mc = document.getElementById("main-content");

  const TAB_MAP = SETTINGS_TAB_MAP;

  let activeTab = "languages";
  for (const [key, val] of Object.entries(TAB_MAP)) {
    if (route.includes(key)) {
      activeTab = val;
      break;
    }
  }

  const tabs = SETTINGS_TABS;

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

  const activeTabObj =
    visibleTabs.find((tab) => tab.id === activeTab) || visibleTabs[0];
  if (!activeTabObj) {
    mc.innerHTML = "";
    return;
  }
  const activeTabLabel = t(
    activeTabObj.i18n,
    activeTabObj.fallback || activeTabObj.id,
  );

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
