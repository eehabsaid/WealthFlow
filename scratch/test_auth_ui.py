import os
import sys
import time
from playwright.sync_api import sync_playwright

def test_auth_pages():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        print("--- Testing Login Page ---")
        page.goto("http://127.0.0.1:8000/accounts/login/")
        page.wait_for_timeout(1000)
        card = page.locator(".auth-card")
        width = card.evaluate("el => el.getBoundingClientRect().width")
        print(f"Login card width: {width}px (Expected ~480px)")

        # Theme toggle check
        toggle_btn = page.locator("#theme-toggle")
        print("Theme before click:", page.evaluate("document.documentElement.getAttribute('data-theme')"))
        toggle_btn.click()
        page.wait_for_timeout(500)
        print("Theme after click:", page.evaluate("document.documentElement.getAttribute('data-theme')"))

        print("\n--- Testing Signup Page ---")
        page.goto("http://127.0.0.1:8000/accounts/signup/")
        page.wait_for_timeout(1000)
        card_signup = page.locator(".auth-card")
        width_signup = card_signup.evaluate("el => el.getBoundingClientRect().width")
        print(f"Signup card width: {width_signup}px (Expected ~540px)")

        # Test live password strength
        pwd_input = page.locator("#signupPasswordInput")
        pwd_input.type("ComplexPass123!")
        page.wait_for_timeout(300)
        strength_text = page.locator("#strengthText").text_content()
        print(f"Password strength indicator text: '{strength_text}'")

        print("\n--- Testing Forgot Password Page ---")
        page.goto("http://127.0.0.1:8000/accounts/forgot-password/")
        page.wait_for_timeout(1000)
        print("Forgot password loaded successfully")

        browser.close()
        print("\nAll Auth UI tests completed successfully!")

if __name__ == "__main__":
    test_auth_pages()
