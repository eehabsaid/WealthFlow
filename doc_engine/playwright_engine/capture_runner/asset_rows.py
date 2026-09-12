"""AssetRowsMixin: per-row View/Edit modal capture for asset table pages.
See this package's __init__.py for the sibling list and composition
conventions."""
from playwright.sync_api import Page

from doc_engine.services.navigation_planner import sanitize_filename
from .helpers import log, check_cancelled_and_exit


class AssetRowsMixin:
    def process_asset_rows(self, page: Page, route_prefix: str) -> None:
        # Order matches the actual page layout, top to bottom: the "Add New
        # Asset" button sits above the table, so its modal is captured first;
        # per-row View/Edit actions (further down the page, one per existing
        # row) are captured second. This keeps generated docs in the same
        # visual order a user encounters them in the app.
        log('  -> Processing Add New Asset modal combinations...')
        try:
            add_btn_clicked = page.evaluate("""() => {
                const btn = document.querySelector('button[onclick*="showFixedAssetModal"]');
                if (btn) { btn.click(); return true; }
                return false;
            }""")

            if add_btn_clicked:
                is_modal_visible = False
                try:
                    page.wait_for_selector('.modal.show', timeout=5000)
                    is_modal_visible = True
                except Exception:
                    is_modal_visible = False

                if is_modal_visible:
                    asset_types = page.evaluate("""() => {
                        const select = document.querySelector('select#fa_type');
                        if (!select) return [];
                        return Array.from(select.options)
                            .filter(opt => opt.value)
                            .map(opt => ({ value: opt.value, text: opt.textContent.trim() }));
                    }""")

                    for t_info in asset_types:
                        check_cancelled_and_exit(self.manifest_service)
                        log(f"     -> Selecting Add asset type: {t_info['text']}")
                        page.evaluate("""() => {
                            const generalTab = document.getElementById('general-tab');
                            if (generalTab) generalTab.click();
                        }""")
                        page.wait_for_timeout(500)

                        page.select_option('select#fa_type', t_info['value'])
                        page.evaluate("""() => {
                            const select = document.querySelector('select#fa_type');
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                        }""")
                        page.wait_for_timeout(500)

                        type_filename = sanitize_filename(t_info['value'])
                        self.global_context["modal_id"] = f"add_{type_filename}"
                        self.capture_modal_tabs(page, f"{route_prefix}_add_{type_filename}", close_after=False)
                        self.global_context["modal_id"] = None

                    self.ensure_modals_closed(page)
                else:
                    log("     Add Asset modal did not visibly open.")
        except Exception as e:
            log(f"     Failed to process Add New Asset: {e}")
        finally:
            self.ensure_modals_closed(page)

        log('  -> Processing per-type asset modals (View & Edit)...')

        page.evaluate("""async () => {
            if (typeof fixedAssetsState !== 'undefined' && fixedAssetsState.loadAssets && (!fixedAssetsState.assets || fixedAssetsState.assets.length === 0)) {
                try { await fixedAssetsState.loadAssets(); } catch(e) {}
            }
            let attempts = 0;
            while (attempts < 20) {
                if (typeof fixedAssetsState !== 'undefined' && fixedAssetsState.assets && fixedAssetsState.assets.length > 0) {
                    return true;
                }
                await new Promise(resolve => setTimeout(resolve, 250));
                attempts++;
            }
            return false;
        }""")

        distinct_assets = page.evaluate(r"""() => {
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
            if (map.size === 0) {
                const rows = Array.from(document.querySelectorAll('#assets-table tbody tr, .table tbody tr'));
                rows.forEach((tr, i) => {
                    const editBtn = tr.querySelector('button[onclick*="showFixedAssetModal"], button[onclick*="openGold"]');
                    const viewBtn = tr.querySelector('button[onclick*="showFixedAssetDetails"], button[onclick*="showGold"]');
                    const typeTd = tr.querySelector('td:nth-child(2)');
                    const assetType = typeTd ? typeTd.textContent.trim() : ('AssetType_' + i);
                    const isGold = assetType.toLowerCase() === 'gold';
                    if (editBtn || viewBtn) {
                        const onclick = (editBtn || viewBtn).getAttribute('onclick') || '';
                        const idMatch = onclick.match(/\((\d+)/);
                        const id = idMatch ? parseInt(idMatch[1], 10) : (i + 1);
                        if (!map.has(assetType)) {
                            map.set(assetType, { id, type: assetType, isGold, purity: isGold ? '24k' : null });
                        }
                    }
                });
            }
            return Array.from(map.values());
        }""")

        if not distinct_assets or len(distinct_assets) == 0:
            log("     No fixed assets found in the table. Skipping View/Edit per-row capture.")
            return

        self.manifest_service.update_status('running', 'Discovering Assets...')
        for info in distinct_assets:
            check_cancelled_and_exit(self.manifest_service)
            asset_type = info.get("type", "Other Assets")
            log(f"     -> Selecting View asset type: {asset_type}")

            view_clicked = page.evaluate("""(assetInfo) => {
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
            }""", info)

            if view_clicked:
                self.global_context["modal_id"] = f"view_{sanitize_filename(asset_type.lower())}"
                self.capture_modal_tabs(page, f"fixed_assets_assets_view_{sanitize_filename(asset_type.lower())}", close_after=False)
                self.global_context["modal_id"] = None
                self.ensure_modals_closed(page)

            log(f"     -> Selecting Edit asset type: {asset_type}")
            edit_clicked = page.evaluate("""(assetInfo) => {
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
            }""", info)

            if edit_clicked:
                self.global_context["modal_id"] = f"edit_{sanitize_filename(asset_type.lower())}"
                self.capture_modal_tabs(page, f"fixed_assets_assets_edit_{sanitize_filename(asset_type.lower())}", close_after=False)
                self.global_context["modal_id"] = None
                self.ensure_modals_closed(page)

