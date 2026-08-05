import sys
import os
import time

sys.path.insert(0, r"d:\MyApps\WealthFlow")
os.environ['DJANGO_SETTINGS_MODULE'] = 'wealthflow.settings'

def run():
    import django
    django.setup()

    from playwright.sync_api import sync_playwright
    from tests.core.test_context import TestContext

    out_dir = r"C:\Users\ehab.alqabbani\.gemini\antigravity\brain\88030822-0997-48fc-bf5b-17fe11e74582\screenshots"
    os.makedirs(out_dir, exist_ok=True)

    with sync_playwright() as p:
        test_ctx = TestContext(p, headed=False, slow_mo=50)
        print("Logging in...")
        test_ctx.login()
        time.sleep(2)

        page = test_ctx.page

        # Arabic Dark Mode
        print("Switching language to Arabic Dark...")
        test_ctx.set_language("ar")
        test_ctx.set_theme("dark")
        time.sleep(2)

        page.evaluate("sessionStorage.setItem('wf_balance_active_tab', 'currency_exchange')")
        test_ctx.goto_route("#balance")
        time.sleep(2)
        if page.query_selector("#bal-tab-currency_exchange"):
            page.click("#bal-tab-currency_exchange")
            time.sleep(2)

        page.click("button[onclick='showExchangeModal()']")
        time.sleep(2)

        if page.query_selector("#ce_from_balance"):
            page.click("#ce_from_balance")
            time.sleep(1)

        path_modal_options_ar = os.path.join(out_dir, "03_modal_options_ar.png")
        page.screenshot(path=path_modal_options_ar)
        print(f"Saved: {path_modal_options_ar}")

        # English Light Mode
        print("Switching to EN Light...")
        test_ctx.set_language("en")
        page.evaluate("if (typeof toggleTheme === 'function') toggleTheme();")
        time.sleep(2)

        page.click("#ce_from_balance")
        time.sleep(1)

        path_modal_options_light = os.path.join(out_dir, "07_modal_options_light.png")
        page.screenshot(path=path_modal_options_light)
        print(f"Saved: {path_modal_options_light}")

        test_ctx.close()

if __name__ == "__main__":
    run()
