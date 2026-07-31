import os
import sys
import time
from playwright.sync_api import sync_playwright

def run_checklist_verification():
    viewports = [
        {'width': 320, 'height': 568},
        {'width': 375, 'height': 667},
        {'width': 414, 'height': 896},
        {'width': 768, 'height': 1024},
        {'width': 1024, 'height': 768},
        {'width': 1366, 'height': 768},
        {'width': 1920, 'height': 1080},
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        print("=== 1. VIEWPORT & RESPONSIVE VALIDATION ===")
        for vp in viewports:
            context = browser.new_context(viewport=vp)
            page = context.new_page()
            page.goto("http://127.0.0.1:8000/accounts/login/")
            page.wait_for_timeout(300)

            # Check horizontal scrolling
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            client_width = page.evaluate("document.documentElement.clientWidth")
            has_overflow = scroll_width > client_width
            print(f"Viewport {vp['width']}x{vp['height']}: ScrollWidth={scroll_width}, ClientWidth={client_width}, Overflow={has_overflow}")

            # Check card width
            card_w = page.locator(".auth-card").evaluate("el => el.getBoundingClientRect().width")
            print(f"  Card Width at {vp['width']}px: {card_w:.1f}px")
            context.close()

        print("\n=== 2. RTL & ARABIC VERIFICATION ===")
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        page.goto("http://127.0.0.1:8000/accounts/login/")
        page.wait_for_timeout(300)

        # Switch to Arabic
        page.select_option("#authLanguageSelect", "ar")
        page.wait_for_timeout(500)

        dir_attr = page.evaluate("document.documentElement.getAttribute('dir')")
        lang_attr = page.evaluate("document.documentElement.getAttribute('lang')")
        title_text = page.title()
        print(f"RTL check: dir='{dir_attr}', lang='{lang_attr}', title='{title_text}'")

        # Verify eye button position in input group
        btn_eye_rect = page.locator(".btn-eye").evaluate("el => el.getBoundingClientRect()")
        inp_rect = page.locator("#passwordInput").evaluate("el => el.getBoundingClientRect()")
        print(f"Input Group RTL check: Input X={inp_rect['x']:.1f}, Eye X={btn_eye_rect['x']:.1f}")

        print("\n=== 3. THEME TOGGLE VERIFICATION ===")
        print("Theme before click:", page.evaluate("document.documentElement.getAttribute('data-theme')"))
        page.click("#theme-toggle")
        page.wait_for_timeout(300)
        print("Theme after click:", page.evaluate("document.documentElement.getAttribute('data-theme')"))

        print("\n=== 4. ACCESSIBILITY & TAB NAVIGATION ===")
        page.goto("http://127.0.0.1:8000/accounts/login/")
        page.wait_for_timeout(300)

        page.focus("#loginUsernameInput")
        focused_id = page.evaluate("document.activeElement.id")
        print("Initial focus ID:", focused_id)
        page.keyboard.press("Tab")
        focused_id_2 = page.evaluate("document.activeElement.id")
        print("After Tab focus ID:", focused_id_2)

        browser.close()
        print("\nVerification completed successfully!")

if __name__ == "__main__":
    run_checklist_verification()
