"use strict";

document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    const emailInput = document.querySelector('input[name="email"]');
    if (emailInput && document.activeElement !== emailInput && !emailInput.value) {
      emailInput.focus();
    }
  }, 100);

  const forgotContent = document.getElementById("forgotContent");
  const successAlert = document.querySelector(".alert-dark-success");

  function renderSuccessCard() {
    if (!forgotContent) return;
    forgotContent.innerHTML = `
            <div class="auth-success-card text-center py-3">
                <div class="success-icon mb-3" style="font-size: 3rem; color: var(--wf-auth-green);">
                    <i class="bi bi-check-circle-fill"></i>
                </div>
                <h4 style="font-size: 18px; font-weight: 700; margin-bottom: 8px;" data-i18n="auth_check_email_title">Check your email</h4>
                <p class="text-secondary mt-2 mb-4" style="font-size: 13px; line-height: 1.6; color: var(--wf-auth-text-secondary);" data-i18n="auth_check_email_msg">
                    Check your email. If an account exists, a password reset link has been sent.
                </p>
                <a href="/accounts/login/" class="btn-submit" style="text-decoration:none;" data-i18n="auth_back_to_login">Back to Login</a>
            </div>
        `;
    if (window.WFAuth && window.WFAuth.loadLanguage) {
      const currentLang = localStorage.getItem("lang") || "en";
      window.WFAuth.loadLanguage(currentLang);
    }
  }

  if (successAlert) {
    renderSuccessCard();
  }
});
