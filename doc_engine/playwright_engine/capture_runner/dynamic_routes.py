"""DynamicRoutesMixin: injects routes discovered only at runtime (not
declared in inventory.json) into the capture plan. See this package's
__init__.py for the sibling list and composition conventions."""
from typing import Any, Dict, List

from playwright.sync_api import Page

from .helpers import log


class DynamicRoutesMixin:
    def inject_dynamic_routes(self, page: Page, inventory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        companies = page.evaluate("""async () => {
            if (window._companies && window._companies.length > 0) {
                return window._companies.map(c => ({
                    name: c.display_name || c.name,
                    id: String(c.id),
                    route: `employment-${c.id}`
                }));
            }
            try {
                const res = await fetch('/api/companies/');
                const data = await res.json();
                const comps = data.companies || [];
                if (comps.length > 0) {
                    return comps.map(c => ({
                        name: c.display_name || c.name,
                        id: String(c.id),
                        route: `employment-${c.id}`
                    }));
                }
            } catch (e) {}
            const links = Array.from(document.querySelectorAll('.employer-tab, [data-employer-id], button.nav-item[data-route^="employment-"], button.nav-item[data-route^="salary-"]'));
            return links.map(link => {
                const cId = link.getAttribute('data-employer-id') || (link.getAttribute('data-route') || '').replace(/^(salary|employment)-/, '');
                return {
                    name: link.textContent.trim(),
                    id: String(cId),
                    route: `employment-${cId}`
                };
            });
        }""")

        if companies and len(companies) > 0:
            log(f"Discovered {len(companies)} companies for Employment tabs.")
            emp_tabs = []
            for i, c in enumerate(companies):
                nested = []
                if i == len(companies) - 1:
                    nested = [
                        {"name": "Add Salary Entry", "type": "modal", "trigger": f"eval:showSalaryModal(null, {c['id']})"},
                        {"name": "Edit Salary Entry", "type": "modal", "trigger": f"eval:const btn = document.querySelector('.btn-icon[onclick*=\"showSalaryModal\"], button[onclick*=\"showSalaryModal\"]'); if(btn) btn.click(); else showSalaryModal(null, {c['id']});"},
                        {"name": "Per Diem List", "type": "modal", "trigger": f"eval:showPerDiemListModal({c['id']})"},
                        {"name": "Add Per Diem", "type": "modal", "trigger": f"eval:showPerDiemFormModal(null, {c['id']}, new Date().getFullYear())"}
                    ]

                emp_tabs.append({
                    "name": c['name'],
                    "id": str(c['id']),
                    "nested_navigation": nested
                })

            emp_item = None
            for item in inventory:
                if item.get("route") == "employment":
                    emp_item = item
                    break

            if emp_item:
                emp_item["tabs"] = emp_tabs
            else:
                target_index = -1
                for idx, item in enumerate(inventory):
                    if item.get("route") == "financial-advisor":
                        target_index = idx
                        break

                new_entry = {
                    "route": "employment",
                    "title": "Employment",
                    "tabs": emp_tabs
                }
                if target_index != -1:
                    inventory.insert(target_index + 1, new_entry)
                else:
                    inventory.append(new_entry)

        return inventory


