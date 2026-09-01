"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const passwordInput = document.getElementById("signupPasswordInput");
  const confirmInput = document.getElementById("signupConfirmPasswordInput");
  const usernameInput = document.getElementById("signupUsernameInput");
  const emailInput = document.getElementById("signupEmailInput");
  const strengthFill = document.getElementById("strengthFill");
  const strengthText = document.getElementById("strengthText");
  const matchWarning = document.getElementById("passwordMatchWarning");
  const usernameHint = document.getElementById("usernameHint");
  const emailHint = document.getElementById("emailHint");

  // Auto-redirect if signup succeeded (success_key present)
  const successAlert = document.querySelector(".alert-dark-success");
  if (successAlert) {
    setTimeout(() => {
      window.location.href = "/accounts/status/?status=pending";
    }, 1500);
  }

  if (window.WFAuth && window.WFAuth.setupCapsLockListener) {
    window.WFAuth.setupCapsLockListener("signupPasswordInput", "signupCapsLockWarning");
  }

  function calculateStrength(pwd) {
    if (!pwd) return { score: 0, labelKey: "", color: "" };
    let score = 0;
    if (pwd.length >= 8) score += 25;
    if (pwd.length >= 12) score += 15;
    if (/[A-Z]/.test(pwd)) score += 20;
    if (/[0-9]/.test(pwd)) score += 20;
    if (/[^A-Za-z0-9]/.test(pwd)) score += 20;
    score = Math.min(score, 100);

    let labelKey = "auth_str_weak";
    let color = "#ff4d6d";

    if (score >= 85) {
      labelKey = "auth_str_very_strong";
      color = "#8b5cf6";
    } else if (score >= 65) {
      labelKey = "auth_str_strong";
      color = "#00d68f";
    } else if (score >= 40) {
      labelKey = "auth_str_medium";
      color = "#f59e0b";
    }

    return { score, labelKey, color };
  }

  function updateStrength() {
    if (!passwordInput || !strengthFill) return;
    const pwd = passwordInput.value;
    if (!pwd) {
      strengthFill.style.width = "0%";
      if (strengthText) strengthText.textContent = "";
      return;
    }

    const { score, labelKey, color } = calculateStrength(pwd);
    strengthFill.style.width = score + "%";
    strengthFill.style.backgroundColor = color;

    if (strengthText) {
      strengthText.setAttribute("data-i18n", labelKey);
      strengthText.style.color = color;
      // Lookup translation if available
      const translations = localStorage.getItem("lang");
      if (labelKey === "auth_str_very_strong") strengthText.textContent = "Very Strong";
      else if (labelKey === "auth_str_strong") strengthText.textContent = "Strong";
      else if (labelKey === "auth_str_medium") strengthText.textContent = "Medium";
      else strengthText.textContent = "Weak";
    }
  }

  function checkMatch() {
    if (!passwordInput || !confirmInput || !matchWarning) return;
    if (confirmInput.value && passwordInput.value !== confirmInput.value) {
      matchWarning.style.display = "block";
      confirmInput.classList.add("is-invalid-custom");
      confirmInput.classList.remove("is-valid-custom");
    } else if (confirmInput.value && passwordInput.value === confirmInput.value) {
      matchWarning.style.display = "none";
      confirmInput.classList.remove("is-invalid-custom");
      confirmInput.classList.add("is-valid-custom");
    } else {
      matchWarning.style.display = "none";
      confirmInput.classList.remove("is-invalid-custom", "is-valid-custom");
    }
  }

  function validateUsername() {
    if (!usernameInput || !usernameHint) return;
    const val = usernameInput.value.trim();
    if (!val) {
      usernameHint.style.display = "none";
      usernameInput.classList.remove("is-invalid-custom", "is-valid-custom");
      return;
    }
    if (val.length < 3) {
      usernameHint.textContent = "Username must be at least 3 characters";
      usernameHint.className = "field-hint hint-error";
      usernameHint.style.display = "block";
      usernameInput.classList.add("is-invalid-custom");
      usernameInput.classList.remove("is-valid-custom");
    } else if (!/^[a-zA-Z0-9_.-]+$/.test(val)) {
      usernameHint.textContent = "Letters, numbers, and _ . - only";
      usernameHint.className = "field-hint hint-error";
      usernameHint.style.display = "block";
      usernameInput.classList.add("is-invalid-custom");
      usernameInput.classList.remove("is-valid-custom");
    } else {
      usernameHint.textContent = "✓ Username format valid";
      usernameHint.className = "field-hint hint-success";
      usernameHint.style.display = "block";
      usernameInput.classList.remove("is-invalid-custom");
      usernameInput.classList.add("is-valid-custom");
    }
  }

  function validateEmail() {
    if (!emailInput || !emailHint) return;
    const val = emailInput.value.trim();
    if (!val) {
      emailHint.style.display = "none";
      emailInput.classList.remove("is-invalid-custom", "is-valid-custom");
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(val)) {
      emailHint.textContent = "Please enter a valid email address";
      emailHint.className = "field-hint hint-error";
      emailHint.style.display = "block";
      emailInput.classList.add("is-invalid-custom");
      emailInput.classList.remove("is-valid-custom");
    } else {
      emailHint.textContent = "✓ Email format valid";
      emailHint.className = "field-hint hint-success";
      emailHint.style.display = "block";
      emailInput.classList.remove("is-invalid-custom");
      emailInput.classList.add("is-valid-custom");
    }
  }

  if (passwordInput) {
    passwordInput.addEventListener("input", () => {
      updateStrength();
      checkMatch();
    });
  }

  if (confirmInput) {
    confirmInput.addEventListener("input", checkMatch);
  }

  if (usernameInput) {
    usernameInput.addEventListener("input", validateUsername);
  }

  if (emailInput) {
    emailInput.addEventListener("input", validateEmail);
  }
});
