"use strict";

/* Animated audio-wave indicator for recording / processing / speaking. */
window.WFSpeech = window.WFSpeech || {};
window.WFSpeech.indicator = {
  show(host, mode, label, before) {
    this.hide(mode);
    if (!host) return;
    const el = document.createElement("div");
    el.className = "wf-wave";
    el.dataset.mode = mode;
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
    el.innerHTML = `<span class="wf-wave-bars" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span><span class="wf-wave-label"></span>`;
    el.querySelector(".wf-wave-label").textContent = label || "";
    host.insertBefore(el, before && before.parentNode === host ? before : null);
  },
  setLabel(mode, label) {
    const el = document.querySelector(`.wf-wave[data-mode="${mode}"] .wf-wave-label`);
    if (el) el.textContent = label;
  },
  hide(mode) {
    document.querySelectorAll(`.wf-wave[data-mode="${mode}"]`).forEach((el) => el.remove());
  },
};
