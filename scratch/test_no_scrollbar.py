import os
import sys
import time
import subprocess
from playwright.sync_api import sync_playwright

def test_scrollbars():
    python_exe = sys.executable
    server_process = subprocess.Popen([python_exe, "manage.py", "runserver", "8012", "--noreload"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2.5)

    try:
        pages_to_test = [
            "/accounts/login/",
            "/accounts/signup/",
            "/accounts/forgot-password/",
            "/accounts/reset-password/test-token/",
            "/accounts/status/?status=pending"
        ]

        viewports = [
            {"name": "Desktop 1920x1080", "width": 1920, "height": 1080},
            {"name": "Laptop 1366x768", "width": 1366, "height": 768},
            {"name": "Tablet 768x1024", "width": 768, "height": 1024},
            {"name": "Mobile 375x667", "width": 375, "height": 667},
            {"name": "Small Mobile 320x568", "width": 320, "height": 568},
            {"name": "Landscape Mobile 667x375", "width": 667, "height": 375},
        ]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            all_passed = True
            for vp in viewports:
                context = browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
                page = context.new_page()

                for route in pages_to_test:
                    url = f"http://127.0.0.1:8012{route}"
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(200)

                    has_v_scrollbar = page.evaluate("document.documentElement.scrollHeight > document.documentElement.clientHeight")
                    has_h_scrollbar = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")

                    if has_v_scrollbar or has_h_scrollbar:
                        print(f"FAILED on {vp['name']} for {route}: VScroll={has_v_scrollbar}, HScroll={has_h_scrollbar}")
                        all_passed = False
                    else:
                        print(f"PASSED on {vp['name']} for {route}: Zero Scrollbars!")

                context.close()

            browser.close()

            if all_passed:
                print("\nALL AUTHENTICATION PAGES PASSED ZERO-SCROLLBAR VALIDATION ACROSS ALL DEVICES!")

    finally:
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    test_scrollbars()
