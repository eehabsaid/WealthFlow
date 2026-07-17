// capture_pages.js
const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');

const host = process.env.DOC_HOST || '127.0.0.1';
const port = process.env.DOC_PORT || '8001';

const CONFIG = {
  baseURL: `http://${host}:${port}`,
  username: process.env.WF_USERNAME || 'eehab_said',
  password: process.env.WF_PASSWORD || 'Eehabdev1',
  theme: process.env.DOC_THEME || 'dark', // 'dark' or 'light'
  language: process.env.DOC_LANG || 'en', // e.g. 'en', 'ar', 'fr', 'de'
  device: process.env.DOC_DEVICE || null, // e.g. 'iPhone 13'
};

CONFIG.outputDir = path.join(__dirname, '..', 'docs', 'screenshots');

const originalLog = console.log;
const originalWarn = console.warn;
const originalError = console.error;

function formatTime() {
    const now = new Date();
    return `[${now.toTimeString().split(' ')[0]}]`;
}

console.log = (...args) => originalLog(formatTime(), ...args);
console.warn = (...args) => originalWarn(formatTime(), ...args);
console.error = (...args) => originalError(formatTime(), ...args);

const INVENTORY_RAW = require('./inventory.json');
// Deep copy the inventory to avoid mutating the require cache if we modify it
let INVENTORY = JSON.parse(JSON.stringify(INVENTORY_RAW));

function sanitizeFilename(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}

// Like sanitizeFilename but falls back to fallbackId when the name contains
// only non-ASCII characters (e.g. Arabic) that sanitize to an empty string.
function safeFilename(name, fallbackId) {
  const s = sanitizeFilename(name);
  if (s) return s;
  // Name was entirely non-ASCII (e.g. Arabic). Use the DOM id instead.
  // Strip common suffixes like "-tab" or "_tab" so the filename matches English equivalents.
  const cleanId = (fallbackId || 'tab').replace(/[-_]tab$/i, '');
  return sanitizeFilename(cleanId);
}

async function waitForUIReady(page) {
  await page.waitForLoadState('networkidle');
  try {
    await page.waitForSelector('.spinner-overlay', { state: 'hidden', timeout: 3000 });
  } catch (e) {}
  await page.waitForTimeout(1000); 
}

// Waits for charts to fully render by dispatching a resize event (forces
// Chart.js and ApexCharts to recalculate) then scrolls through all canvas
// elements and waits for them to settle. Used on all chart-heavy pages.
async function waitForCharts(page) {
  // Wait for Bootstrap tab transitions (usually 150ms) to complete before dispatching resize
  await page.waitForTimeout(1000);

  await page.evaluate(async () => {
    // Re-assert Apex animations off in case anything reset it
    if (window.Apex) window.Apex.chart = { animations: { enabled: false } };
    // Force a resize so charts recalculate their canvas dimensions
    window.dispatchEvent(new Event('resize'));
    await new Promise(r => setTimeout(r, 500));
    // Scroll through every canvas/chart element to trigger lazy renders.
    // Must include '.card' because WealthFlow uses IntersectionObserver on cards
    // to trigger the initial network requests for chart data.
    const elements = document.querySelectorAll('.card, canvas, [id*="chart"], .apexcharts-canvas, .chart-container');
    for (const el of elements) {
      el.scrollIntoView({ behavior: 'auto', block: 'center' });
      await new Promise(r => setTimeout(r, 80));
    }
    window.scrollTo(0, 0);
    const mainContent = document.querySelector('.main-content, #main-wrapper, main, .container-fluid');
    if (mainContent) mainContent.scrollTo(0, 0);
  });
  await page.waitForTimeout(2000);
}

const STATUS_FILE = path.join(__dirname, '..', 'docs', 'generated', 'capture_status.json');
const CANCEL_FLAG = path.join(__dirname, '..', 'docs', 'generated', 'cancel.flag');
const startTime = new Date().toISOString();
let totalItems = 0;
let currentProgress = 0;
let screenshotsCount = 0;
let failedPages = [];

function updateStatus(status, pageName = '', tabName = '', error = '') {
  const now = new Date();
  const elapsed = Math.round((now - new Date(startTime)) / 1000);
  const data = {
    status: status,
    page: pageName,
    tab: tabName,
    language: CONFIG.language,
    theme: CONFIG.theme,
    device: CONFIG.device || 'desktop',
    progress: currentProgress,
    total: totalItems,
    screenshots_count: screenshotsCount,
    started_at: startTime,
    finished_at: status === 'finished' || status === 'cancelled' ? now.toISOString() : '',
    elapsed_seconds: elapsed,
    error: error,
    failed_pages: failedPages
  };
  const dir = path.dirname(STATUS_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(STATUS_FILE, JSON.stringify(data, null, 2));
}

function checkCancelled() {
  if (fs.existsSync(CANCEL_FLAG)) {
    console.log('\n[!] Cancellation requested. Stopping capture.');
    updateStatus('cancelled');
    process.exit(0);
  }
}

const CHART_ROUTES = new Set(['dashboard', 'financial-advisor', 'advanced-reports', 'reports']);

async function captureScreenshot(page, filename) {
  if (!fs.existsSync(CONFIG.outputDir)) {
    fs.mkdirSync(CONFIG.outputDir, { recursive: true });
  }
  const filepath = path.join(CONFIG.outputDir, `${filename}.png`);
  
  const styleHandle = await page.addStyleTag({ content: `
    .modal.show {
      position: absolute !important;
      overflow: visible !important;
      height: auto !important;
      bottom: auto !important;
    }
    .modal-dialog {
      height: auto !important;
      max-height: none !important;
    }
    .modal-content {
      overflow: visible !important;
      height: auto !important;
      max-height: none !important;
    }
    .modal-body {
      overflow: visible !important;
      height: auto !important;
      max-height: none !important;
    }
    body {
      height: auto !important;
      overflow: auto !important;
    }
  `});

  await page.waitForTimeout(500);
  await page.screenshot({ path: filepath, fullPage: true });
  await page.evaluate((el) => el.remove(), styleHandle);
  
  screenshotsCount++;
  
  console.log(`[Captured] ${filepath}`);
}

async function captureModalTabs(page, filePrefix, closeAfter = true) {
  await page.waitForTimeout(1000);
  await waitForUIReady(page);
  
  const isModalVisible = await page.evaluate(() => document.querySelector('.modal.show') !== null);
  if (!isModalVisible) {
    console.warn(`     Modal did not successfully open. Skipping its tabs.`);
    return;
  }
  
  const tabs = await page.evaluate(() => {
    const tabButtons = Array.from(document.querySelectorAll('.modal.show .nav-tabs .nav-item button, .modal.show .nav-tabs .nav-link, .modal.show .nav-pills .nav-item button, .modal.show .nav-pills .nav-link'));
    const visibleButtons = tabButtons.filter(b => {
      const li = b.closest('li');
      if (li && (li.classList.contains('d-none') || li.style.display === 'none')) return false;
      return true;
    });
    
    return visibleButtons.map((b, i) => {
      if (!b.id) b.id = 'temp-modal-tab-' + i;
      // Use data-i18n attribute as stable filename key — it is always the English
      // translation key regardless of the active language (e.g. Arabic, French).
      // Fall back to the button id stripped of the common -tab / _tab suffix.
      const dataI18n = b.getAttribute('data-i18n');
      const cleanId  = b.id.replace(/[-_]tab$/i, '');
      const filenameKey = dataI18n || cleanId || ('tab_' + i);
      return { id: b.id, name: b.textContent.trim(), filenameKey };
    });
  });
  
  if (tabs.length > 0) {
    for (const t of tabs) {
      console.log(`        -> Capturing modal tab: ${t.name}`);
      await page.evaluate((tabId) => {
        const btn = document.getElementById(tabId);
        if (btn) btn.click();
      }, t.id);
      await page.waitForTimeout(500);
      await captureScreenshot(page, `${filePrefix}_${sanitizeFilename(t.filenameKey)}`);
    }
  } else {
    await captureScreenshot(page, filePrefix);
  }
  
  if (closeAfter) {
    const closeBtn = await page.$('.modal.show .btn-close, .modal.show [data-bs-dismiss="modal"]');
    if (closeBtn) {
      await closeBtn.click({ force: true });
    } else {
      await page.keyboard.press('Escape');
    }
    await page.waitForTimeout(1000);
  }
}

async function processTabs(page, tabs, prefix) {
  for (const tab of tabs) {
    console.log(`  -> Clicking tab: ${tab.name}`);
    await page.evaluate((tabId) => {
      const el = document.getElementById(tabId + '-tab') || document.querySelector(`[data-bs-target="#${tabId}"]`) || document.getElementById(tabId);
      if (el) el.click();
    }, tab.id);

    await waitForUIReady(page);
    await page.waitForTimeout(2000);
    
    await captureScreenshot(page, `${prefix}_${safeFilename(tab.name, tab.id)}`);
    
    if (tab.nested_navigation) {
        await processModals(page, tab.nested_navigation, `${prefix}_${safeFilename(tab.name, tab.id)}`);
    }
  }
}

async function processAssetRows(page, routePrefix) {
  console.log('  -> Processing per-type asset modals (View & Edit)...');
  
  await page.evaluate(async () => {
     let attempts = 0;
     while (attempts < 20) {
        if (typeof fixedAssetsState !== 'undefined' && fixedAssetsState.assets && fixedAssetsState.assets.length > 0) {
           return true;
        }
        await new Promise(resolve => setTimeout(resolve, 250));
        attempts++;
     }
     return false;
  });

  const distinctAssets = await page.evaluate(() => {
    const assets = (typeof fixedAssetsState !== 'undefined' && fixedAssetsState.assets) ? fixedAssetsState.assets : [];
    const map = new Map();
    for (const asset of assets) {
      const assetType = asset.asset_type || asset.type || 'Other Assets';
      const isGold = assetType.toLowerCase() === 'gold';
      const purity = isGold ? (asset.gold_details?.purity || asset.purity || '24k') : null;
      if (!map.has(assetType)) {
        map.set(assetType, { id: asset.id, type: assetType, isGold, purity });
      }
    }
    return Array.from(map.values());
  });

  if (distinctAssets.length === 0) {
    console.warn(`     No fixed assets found in the table. Skipping View/Edit per-row capture.`);
  }

  for (const info of distinctAssets) {
      const type = info.type;
      console.log(`     -> Selecting View asset type: ${type}`);
      const viewClicked = await page.evaluate((assetInfo) => {
         if (assetInfo.isGold) {
             if (typeof openGoldPurchaseDetails === 'function') {
                 openGoldPurchaseDetails(assetInfo.id, assetInfo.purity || '24k');
                 return true;
             }
         } else {
             if (typeof showFixedAssetDetails === 'function') {
                 showFixedAssetDetails(assetInfo.id);
                 return true;
             }
         }
         return false;
      }, info);
      
      if (viewClicked) {
         // type comes from the data model (always English), use safeFilename with type as fallback
         await captureModalTabs(page, `fixed_assets_assets_view_${sanitizeFilename(type.toLowerCase())}`, false);
         
         await page.evaluate(() => {
            const closeBtn = document.querySelector('.modal.show .btn-close');
            if (closeBtn) closeBtn.click();
         });
         await page.waitForTimeout(500);
      }

      console.log(`     -> Selecting Edit asset type: ${type}`);
      const editClicked = await page.evaluate((assetInfo) => {
         if (assetInfo.isGold) {
             if (typeof openGoldPurchaseEditor === 'function') {
                 openGoldPurchaseEditor(assetInfo.id, assetInfo.purity || '24k');
                 return true;
             }
         } else {
             if (typeof showFixedAssetModal === 'function') {
                 showFixedAssetModal(assetInfo.id);
                 return true;
             }
         }
         return false;
      }, info);
      
      if (editClicked) {
         // type comes from the data model (always English), use safeFilename with type as fallback
         await captureModalTabs(page, `fixed_assets_assets_edit_${sanitizeFilename(type.toLowerCase())}`, false);
         
         await page.evaluate(() => {
            const closeBtn = document.querySelector('.modal.show .btn-close');
            if (closeBtn) closeBtn.click();
         });
         await page.waitForTimeout(500);
      }
  }

  console.log('  -> Processing Add New Asset modal combinations...');
  try {
    const addBtnClicked = await page.evaluate(() => {
      const btn = document.querySelector('button[onclick*="showFixedAssetModal"]');
      if (btn) { btn.click(); return true; }
      return false;
    });

    if (addBtnClicked) {
      await page.waitForTimeout(1000);
      await waitForUIReady(page);
      
      const isModalVisible = await page.evaluate(() => document.querySelector('.modal.show') !== null);
      if (isModalVisible) {
        const assetTypes = await page.evaluate(() => {
          const select = document.querySelector('select#fa_type');
          if (!select) return [];
          return Array.from(select.options)
            .filter(opt => opt.value) // Skip placeholder
            .map(opt => ({ value: opt.value, text: opt.textContent.trim() }));
        });
        
        for (const type of assetTypes) {
          console.log(`     -> Selecting Add asset type: ${type.text}`);
          
          await page.evaluate(() => {
            const generalTab = document.getElementById('general-tab');
            if (generalTab) generalTab.click();
          });
          await page.waitForTimeout(500);

          await page.selectOption('select#fa_type', type.value);
          await page.evaluate(() => {
            const select = document.querySelector('select#fa_type');
            select.dispatchEvent(new Event('change', { bubbles: true }));
          });
          await page.waitForTimeout(500);
          
          // Use type.value (always English, e.g. "Real Estate") NOT type.text (translated/Arabic)
          // to build the filename so it stays consistent across all languages.
          const typeFilename = sanitizeFilename(type.value);
          await captureModalTabs(page, `${routePrefix}_add_${typeFilename}`, false);
        }
        
        const closeBtn = await page.$('.modal.show .btn-close, .modal.show [data-bs-dismiss="modal"]');
        if (closeBtn) {
          await closeBtn.click({ force: true });
        } else {
          await page.keyboard.press('Escape');
        }
        await page.waitForTimeout(1000);
      } else {
        console.warn(`     Add Asset modal did not visibly open.`);
      }
    }
  } catch (e) {
    console.error(`     Failed to process Add New Asset:`, e.message);
  }
}

async function performLogin(page) {
  console.log(`Capturing Auth Pages...`);
  await page.goto(`${CONFIG.baseURL}/accounts/signup/`);
  await waitForUIReady(page);
  await page.waitForTimeout(500);
  await captureScreenshot(page, 'create_account');

  await page.goto(`${CONFIG.baseURL}/accounts/forgot-password/`);
  await waitForUIReady(page);
  await page.waitForTimeout(500);
  await captureScreenshot(page, 'forgot_password');

  await page.goto(`${CONFIG.baseURL}/accounts/login/`);
  await waitForUIReady(page);
  await page.waitForTimeout(500);
  await captureScreenshot(page, 'login');

  console.log(`Logging in at ${CONFIG.baseURL}...`);
  await page.fill('input[name="username"], input[type="email"]', CONFIG.username);
  await page.fill('input[name="password"], input[type="password"]', CONFIG.password);
  await page.click('button[type="submit"], input[type="submit"], .btn-login');
  await waitForUIReady(page);
}


async function injectDynamicRoutes(page) {
  const companies = await page.evaluate(() => {
    const links = Array.from(document.querySelectorAll('button.nav-item[data-route^="salary-"]'));
    return links.map(link => ({
      name: link.textContent.trim(),
      id: link.getAttribute('data-route').replace('salary-', ''),
      route: link.getAttribute('data-route')
    }));
  });

  if (companies.length > 0) {
    console.log(`Discovered ${companies.length} companies for Salary routes.`);
    const salaryRoutes = companies.map((c, i) => {
      const nested = [];
      if (i === companies.length - 1) {
        nested.push({ name: "Add Salary Entry", type: "modal", trigger: "eval:showSalaryModal(null, " + c.id + ")" });
        nested.push({ name: "Add Perdiem1", type: "modal", trigger: "eval:showPerDiemListModal(" + c.id + ")" });
        nested.push({ name: "Add Perdiem2", type: "modal", trigger: "eval:showPerDiemFormModal(null, " + c.id + ", new Date().getFullYear())" });
      }
      return {
        route: c.route,
        title: `Salary_${sanitizeFilename(c.name.toLowerCase())}`,
        customPrefix: `salary_${i + 1}`,
        nested_navigation: nested
      };
    });
    
    salaryRoutes.push({ "route": "all-companies", "title": "All Companies", "nested_navigation": [{ "name": "Add Company", "type": "modal", "trigger": "showCompanyModal" }] });
    
    const targetIndex = INVENTORY.findIndex(item => item.route === 'financial-advisor');
    INVENTORY.splice(targetIndex + 1, 0, ...salaryRoutes);
  }
}

async function clickTabById(page, tab) {
  return await page.evaluate((tabData) => {
    let target = null;
    
    if (tabData.id) {
      // Try data-bs-target or onclick containing the tab id (language-independent)
      const candidates = Array.from(document.querySelectorAll(`[onclick*="${tabData.id}"], [data-bs-target*="${tabData.id}"]`));
      target = candidates.find(el => !el.closest('#sidebar'));
      
      // Also try getElementById with common -tab suffix (for Bootstrap tabs)
      if (!target) {
        const byId = document.getElementById(tabData.id + '-tab') || document.getElementById(tabData.id);
        if (byId && !byId.closest('#sidebar')) target = byId;
      }
    }
    
    if (!target) {
      // Last resort: match by English name in textContent (works in EN only,
      // but the id-based attempts above cover other languages)
      const elements = Array.from(document.querySelectorAll('button, .nav-link, .nav-item, [role="tab"], .dropdown-item, .wf-dropdown-item'));
      const normalize = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
      const normText = normalize(tabData.name);
      
      let matches = elements.filter(el => !el.closest('#sidebar') && !el.classList.contains('dropdown-toggle'));
      
      target = matches.find(el => el.textContent.trim().toLowerCase() === tabData.name.toLowerCase());
      if (!target) target = matches.find(el => normalize(el.textContent) === normText);
      if (!target) target = matches.find(el => normalize(el.textContent).includes(normText));
    }
    
    if (target) {
      // Use Bootstrap's Tab API to activate the pane if it's a Bootstrap tab
      // (works even when the button is hidden inside an overflow dropdown in RTL).
      // Otherwise, fall back to a standard click for custom tabs (Settings, Reports).
      const isBootstrapTab = target.hasAttribute('data-bs-toggle') || target.hasAttribute('data-bs-target');
      if (isBootstrapTab && window.bootstrap && window.bootstrap.Tab) {
        window.bootstrap.Tab.getOrCreateInstance(target).show();
      } else {
        target.scrollIntoView({ behavior: 'auto', block: 'center' });
        target.click();
      }
      return true;
    }
    return false;
  }, tab);
}

async function processModals(page, routePrefix, modals) {
  for (const modal of modals) {
    try {
      console.log(`  -> Processing modal: ${modal.name}`);
      
      const clicked = await page.evaluate((modal) => {
        const modalName = modal.name;
        const trigger = modal.trigger;
        const buttons = Array.from(document.querySelectorAll('button, a'));
        const safeButtons = buttons.filter(b => !b.closest('#sidebar'));
        
        let target = null;
        
        if (trigger) {
          if (trigger.startsWith('eval:')) {
            const code = trigger.substring(5);
            try {
              eval(code);
              return true;
            } catch (e) {
              return false;
            }
          }
          
          target = safeButtons.find(b => 
            (b.getAttribute('onclick') && b.getAttribute('onclick').toLowerCase().includes(trigger.toLowerCase())) ||
            (b.title && b.title.toLowerCase().includes(trigger.toLowerCase())) ||
            (b.id && b.id.toLowerCase().includes(trigger.toLowerCase())) ||
            (b.getAttribute('data-bs-target') && b.getAttribute('data-bs-target').toLowerCase().includes(trigger.toLowerCase()))
          );
        }
        
        if (!target) {
          target = safeButtons.find(b => b.textContent.toLowerCase().includes(modalName.toLowerCase()));
        }
        
        if (target) {
          target.click();
          return true;
        }
        return false;
      }, modal);

      if (!clicked) {
        console.warn(`     Cannot find trigger for modal: ${modal.name}. Skipping.`);
        continue;
      }

      await captureModalTabs(page, `${routePrefix}_${sanitizeFilename(modal.name)}`, true);
    } catch (err) {
      console.error(`  Failed processing modal ${modal.name}:`, err.message);
    }
  }
}

async function executeWithRetry(actionName, actionFn) {
  try {
    return await actionFn();
  } catch (err) {
    console.warn(`Retry 1 for ${actionName} due to error: ${err.message}`);
    await new Promise(r => setTimeout(r, 2000));
    return await actionFn();
  }
}

async function processPage(page, item) {
  console.log(`\nNavigating to ${item.route} (${item.title})`);
  const routePrefix = item.route.startsWith('/') ? sanitizeFilename(item.route.replace(/\//g, '')) : sanitizeFilename(item.route);

  try {
    if (item.route.startsWith('/')) {
        await page.goto(`${CONFIG.baseURL}${item.route}`);
    } else {
        await page.goto(`${CONFIG.baseURL}/#${item.route}`);
    }
    await waitForUIReady(page);
    if (CHART_ROUTES.has(item.route)) {
        await waitForCharts(page);
    }

    if (item.tabs && item.tabs.length > 0) {
      for (const tab of item.tabs) {
        checkCancelled();
        currentProgress++;
        updateStatus('running', item.title, tab.name);
        try {
          await executeWithRetry(`tab ${tab.name}`, async () => {
              console.log(`  -> Clicking tab: ${tab.name}`);
              const clicked = await clickTabById(page, tab);
              if (!clicked) {
                console.warn(`     Tab button not found for: ${tab.name}. Skipping screenshot.`);
                return;
              }
              await waitForUIReady(page);
              // For chart-heavy routes, wait for every tab's charts to settle
              if (CHART_ROUTES.has(item.route)) {
                await waitForCharts(page);
              } else {
                await page.waitForTimeout(1000);
              }
              if (tab.name === 'Translation Coverage') {
                 await captureScreenshot(page, 'Translation Coverage');
              } else {
                 await captureScreenshot(page, `${routePrefix}_${safeFilename(tab.name, tab.id)}`);
              }
              
              if (item.route === 'fixed-assets' && tab.id === 'assets') {
                 await processAssetRows(page, `${routePrefix}_${safeFilename(tab.name, tab.id)}`);
              } else if (tab.nested_navigation) {
                 await processModals(page, `${routePrefix}_${safeFilename(tab.name, tab.id)}`, tab.nested_navigation);
              }
          });
        } catch (err) {
          console.error(`  Failed to capture tab ${tab.name}:`, err.message);
        }
      }
    } else {
      checkCancelled();
      currentProgress++;
      updateStatus('running', item.title);
      try {
          await executeWithRetry(`page ${item.title}`, async () => {
              await captureScreenshot(page, routePrefix);
              if (item.nested_navigation && (!item.tabs || item.tabs.length === 0)) {
                await processModals(page, routePrefix, item.nested_navigation);
              }
          });
      } catch (err) {
          console.error(`  Failed to capture page ${item.title}:`, err.message);
      }
    }

  } catch (err) {
    console.error(`Failed to process page ${item.route}:`, err.message);
  }
}

(async () => {
  console.log('Starting screenshot generation...');
  console.log(`[CONFIG] Theme: ${CONFIG.theme.toUpperCase()} | Language: ${CONFIG.language.toUpperCase()}`);
  if (CONFIG.device) console.log(`[CONFIG] Device: ${CONFIG.device}`);
  console.log(`[CONFIG] Output folder: ${CONFIG.outputDir}`);
  
  console.log('Cleaning up old screenshots...');
  if (fs.existsSync(CONFIG.outputDir)) {
      fs.rmSync(CONFIG.outputDir, { recursive: true, force: true });
  }
  fs.mkdirSync(CONFIG.outputDir, { recursive: true });

  let contextOptions = { viewport: null };
  let launchArgs = ['--start-maximized'];

  if (CONFIG.device && CONFIG.device !== 'Desktop Chrome') {
      const inventoryPath = path.join(__dirname, 'device_inventory.json');
      if (fs.existsSync(inventoryPath)) {
          const inventory = JSON.parse(fs.readFileSync(inventoryPath, 'utf8'));
          let foundDevice = null;
          if (inventory.categories) {
              for (const cat of Object.keys(inventory.categories)) {
                  foundDevice = inventory.categories[cat].find(d => d.id === CONFIG.device);
                  if (foundDevice) break;
              }
          }
          
          if (foundDevice && foundDevice.execution) {
              const exec = foundDevice.execution;
              if (exec.type === 'current') {
                  contextOptions = { viewport: null };
                  launchArgs = ['--start-maximized'];
              } else if (exec.type === 'viewport') {
                  contextOptions = { viewport: exec.value };
                  launchArgs = [];
              } else if (exec.type === 'playwright') {
                  if (devices[exec.value]) {
                      contextOptions = { ...devices[exec.value] };
                      launchArgs = [];
                  }
              }
          } else {
             // Fallback to older direct playwright device resolution if id not found
             if (devices[CONFIG.device]) {
                 contextOptions = { ...devices[CONFIG.device] };
                 launchArgs = [];
             }
          }
      } else {
          // Fallback if inventory missing
          if (devices[CONFIG.device]) {
              contextOptions = { ...devices[CONFIG.device] };
              launchArgs = [];
          }
      }
  }

  const browser = await chromium.launch({ headless: false, args: launchArgs });
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();

  // Inject Apex + theme + language on every page BEFORE scripts run.
  // This overrides anything left in the browser's localStorage from previous runs.
  await page.addInitScript((cfg) => {
    window.Apex = {
      chart: {
        animations: { enabled: false }
      }
    };

    // Disable Chart.js animations globally
    const existingChart = window.Chart;
    if (existingChart && existingChart.defaults) {
        existingChart.defaults.animation = false;
        if (existingChart.defaults.plugins && existingChart.defaults.plugins.tooltip) {
            existingChart.defaults.plugins.tooltip.animation = false;
        }
    }
    
    let _chart = existingChart;
    Object.defineProperty(window, 'Chart', {
        configurable: true,
        get() { return _chart; },
        set(val) { 
            _chart = val;
            if (val && val.defaults) {
                val.defaults.animation = false;
                val.defaults.responsiveAnimationDuration = 0;
                if (val.defaults.plugins && val.defaults.plugins.tooltip) {
                    val.defaults.plugins.tooltip.animation = false;
                }
            }
        }
    });

    // Force-write theme & language into localStorage before the app reads them
    localStorage.setItem('theme', cfg.theme);
    localStorage.setItem('lang', cfg.language);

    // Apply theme attribute immediately so CSS variables pick it up
    if (cfg.theme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
  }, CONFIG);

  try {
    // Clear ALL browser storage before we start to remove any leftover
    // lang/theme from previous script runs (this is the key fix!)
    await page.goto(`${CONFIG.baseURL}/accounts/login/`);
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await context.clearCookies();
    console.log('[INFO] Browser storage cleared. Starting fresh...');

    await performLogin(page);
    await injectDynamicRoutes(page);

    // Calculate total pages + tabs roughly for progress
    totalItems = INVENTORY.reduce((acc, item) => acc + Math.max(1, (item.tabs || []).length), 0);

    failedPages = [];

    for (const item of INVENTORY) {
      checkCancelled();
      try {
          await processPage(page, item);
      } catch (err) {
          console.error(`Fatal error processing page ${item.route}:`, err.message);
          failedPages.push({ route: item.route, error: err.message });
      }
    }

    if (failedPages.length > 0) {
      console.log('\n--- Capture Completed with Failures ---');
      console.log(failedPages);
    } else {
      console.log('\n--- Capture Completed Successfully ---');
    }
    
    updateStatus('finished');

  } catch (err) {
    console.error('Fatal error during execution:', err);
    updateStatus('failed', '', '', err.message);
  } finally {
    // Clear storage after finishing so the NEXT run always starts clean
    try {
      await page.evaluate(() => {
        localStorage.clear();
        sessionStorage.clear();
      });
      await context.clearCookies();
      console.log('[INFO] Browser storage cleared after run.');
    } catch (e) { /* ignore if page already closed */ }
    await browser.close();
    console.log('Screenshot generation complete.');
  }
})();