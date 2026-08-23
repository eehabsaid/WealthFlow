"""
UI tests for the WealthFlow authentication pages (Login, Signup, Forgot
Password), covering layout, the dark/light theme toggle and the live
password-strength indicator.

Converted from the ad-hoc `scripts/test_auth_ui.py` smoke script into a real
pytest suite with per-check assertions and Allure reporting.

Run with:
    pytest tests/ui/test_auth_ui.py --alluredir=allure-results
    allure serve allure-results
"""
import allure
import pytest

LOGIN_URL = "/accounts/login/"
SIGNUP_URL = "/accounts/signup/"
FORGOT_PASSWORD_URL = "/accounts/forgot-password/"

AUTH_CARD_SELECTOR = ".auth-card"
THEME_TOGGLE_SELECTOR = "#theme-toggle"
SIGNUP_PASSWORD_SELECTOR = "#signupPasswordInput"
STRENGTH_TEXT_SELECTOR = "#strengthText"

# The original script only printed these widths for a human to eyeball; here
# they become real tolerances so a regression actually fails the test.
LOGIN_CARD_EXPECTED_WIDTH = 480
SIGNUP_CARD_EXPECTED_WIDTH = 540
CARD_WIDTH_TOLERANCE = 20

TEST_PASSWORD = "ComplexPass123!"


def _card_width(page, selector=AUTH_CARD_SELECTOR):
    card = page.locator(selector)
    card.wait_for(state="visible")
    return card.evaluate("el => el.getBoundingClientRect().width")


def _current_theme(page):
    return page.evaluate("document.documentElement.getAttribute('data-theme')")


@allure.epic("WealthFlow")
@allure.feature("Authentication UI")
class TestAuthUI:
    @allure.story("Login page")
    @allure.title("Login card renders with the expected width")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_page_card_width(self, page, base_url):
        with allure.step(f"Navigate to {LOGIN_URL}"):
            page.goto(f"{base_url}{LOGIN_URL}")
            page.wait_for_selector(AUTH_CARD_SELECTOR)

        with allure.step("Measure the auth card width"):
            width = _card_width(page)
            allure.attach(
                str(width), name="login-card-width-px", attachment_type=allure.attachment_type.TEXT
            )

        assert width == pytest.approx(LOGIN_CARD_EXPECTED_WIDTH, abs=CARD_WIDTH_TOLERANCE), (
            f"Login card width {width}px is outside the expected "
            f"{LOGIN_CARD_EXPECTED_WIDTH}±{CARD_WIDTH_TOLERANCE}px range"
        )

    @allure.story("Login page")
    @allure.title("Theme toggle switches the page's data-theme attribute")
    @allure.severity(allure.severity_level.NORMAL)
    def test_theme_toggle_switches_theme(self, page, base_url):
        with allure.step(f"Navigate to {LOGIN_URL}"):
            page.goto(f"{base_url}{LOGIN_URL}")
            page.wait_for_selector(THEME_TOGGLE_SELECTOR)

        with allure.step("Record theme before toggling"):
            theme_before = _current_theme(page)
            allure.attach(str(theme_before), name="theme-before", attachment_type=allure.attachment_type.TEXT)

        with allure.step("Click the theme toggle button"):
            page.locator(THEME_TOGGLE_SELECTOR).click()
            page.wait_for_timeout(500)

        with allure.step("Record theme after toggling"):
            theme_after = _current_theme(page)
            allure.attach(str(theme_after), name="theme-after", attachment_type=allure.attachment_type.TEXT)

        assert theme_after != theme_before, (
            f"Theme toggle had no effect: data-theme stayed '{theme_before}'"
        )

    @allure.story("Signup page")
    @allure.title("Signup card renders with the expected width")
    @allure.severity(allure.severity_level.NORMAL)
    def test_signup_page_card_width(self, page, base_url):
        with allure.step(f"Navigate to {SIGNUP_URL}"):
            page.goto(f"{base_url}{SIGNUP_URL}")
            page.wait_for_selector(AUTH_CARD_SELECTOR)

        with allure.step("Measure the auth card width"):
            width = _card_width(page)
            allure.attach(
                str(width), name="signup-card-width-px", attachment_type=allure.attachment_type.TEXT
            )

        assert width == pytest.approx(SIGNUP_CARD_EXPECTED_WIDTH, abs=CARD_WIDTH_TOLERANCE), (
            f"Signup card width {width}px is outside the expected "
            f"{SIGNUP_CARD_EXPECTED_WIDTH}±{CARD_WIDTH_TOLERANCE}px range"
        )

    @allure.story("Signup page")
    @allure.title("Password strength indicator reacts to a strong password")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_signup_password_strength_indicator(self, page, base_url):
        with allure.step(f"Navigate to {SIGNUP_URL}"):
            page.goto(f"{base_url}{SIGNUP_URL}")
            page.wait_for_selector(SIGNUP_PASSWORD_SELECTOR)

        with allure.step("Type a complex password into the signup form"):
            page.locator(SIGNUP_PASSWORD_SELECTOR).type(TEST_PASSWORD)
            page.wait_for_timeout(300)

        with allure.step("Read the strength indicator text"):
            strength_text = page.locator(STRENGTH_TEXT_SELECTOR).text_content()
            allure.attach(
                strength_text or "", name="strength-indicator-text", attachment_type=allure.attachment_type.TEXT
            )

        assert strength_text, "Password strength indicator did not render any text"
        assert strength_text.strip().lower() not in {"", "weak"}, (
            f"Strength indicator still reports '{strength_text}' for a complex password"
        )

    @allure.story("Forgot password page")
    @allure.title("Forgot password page loads successfully")
    @allure.severity(allure.severity_level.MINOR)
    def test_forgot_password_page_loads(self, page, base_url):
        with allure.step(f"Navigate to {FORGOT_PASSWORD_URL}"):
            response = page.goto(f"{base_url}{FORGOT_PASSWORD_URL}")
            page.wait_for_load_state("networkidle")

        with allure.step("Verify the page responded successfully"):
            assert response is not None, "Navigation did not return a response"
            assert response.ok, f"Forgot password page returned status {response.status}"
