/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — DOM Helpers
   ───────────────────────────────────────────────────────────────
   Provides DOM-level utilities: native value descriptor capture,
   focus-safety checks, wrapper/trigger construction, and the
   .value property intercept that keeps the trigger button in sync
   with any external programmatic el.value writes.

   Dependencies : (none — pure DOM utilities)
   Exposes      : window._WF_DP.dom
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  window._WF_DP = window._WF_DP || {};

  /**
   * Read the HTMLInputElement.prototype value descriptor so we can call the
   * original getter/setter safely inside our own property override.
   */
  const _nativeValueDescriptor = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    "value"
  );

  /**
   * Returns true if the element can safely receive focus — i.e. none of its
   * ancestors have aria-hidden="true" and the element itself is not hidden.
   * Focusing an element inside an aria-hidden subtree triggers an
   * accessibility violation (WAI-ARIA spec §6.6.3).
   *
   * @param {Element} el
   * @returns {boolean}
   */
  function _isFocusable(el) {
    if (!el || !document.body.contains(el)) return false;
    let node = el;
    while (node && node !== document.body) {
      if (node.getAttribute("aria-hidden") === "true") return false;
      if (node.hasAttribute("inert")) return false;
      node = node.parentElement;
    }
    return true;
  }

  /**
   * Move focus to document.body as a safe fallback when the intended focus
   * target is inside an aria-hidden/inert subtree.
   *
   * document.body is not focusable by default, so we temporarily set
   * tabindex="-1", focus it, then remove the attribute once focus has moved.
   * This prevents the browser from "restoring" focus to the last-known
   * element in the document — which may be inside a now-hidden modal.
   */
  function _focusBody() {
    const body = document.body;
    const hadTabIndex = body.hasAttribute("tabindex");
    if (!hadTabIndex) body.setAttribute("tabindex", "-1");
    body.focus({ preventScroll: true });
    // Clean up after the browser has processed the focus event.
    if (!hadTabIndex) {
      requestAnimationFrame(() => {
        if (document.activeElement === body) {
          body.removeAttribute("tabindex");
        }
      });
    }
  }

  /**
   * Build the wrapper <div class="wf-dp-wrap"> and move the native input
   * inside it. Transfers any inline style from the native input to the
   * wrapper to preserve the original layout intent (e.g. explicit widths).
   *
   * @param {HTMLInputElement} native
   * @returns {HTMLDivElement} the wrapper element (already inserted in DOM)
   */
  function _buildWrapper(native) {
    const wrap = document.createElement("div");
    wrap.className = "wf-dp-wrap";
    // Transfer any explicit style width/height from native to wrap
    if (native.style.cssText) {
      wrap.setAttribute("style", native.style.cssText);
      native.style.cssText = "";
    }
    // Insert wrapper before native input, move native inside
    native.parentNode.insertBefore(wrap, native);
    wrap.appendChild(native);
    // Add CSS class to native to apply our hiding rules
    native.classList.add("wf-dp-native");
    return wrap;
  }

  /**
   * Install a property override on the native input so that any external
   * `el.value = 'YYYY-MM-DD'` call also triggers the provided callback,
   * which is used to update the trigger button display.
   *
   * @param {HTMLInputElement} native  The original input element
   * @param {Function}         onSet   Callback invoked after the native value is written
   */
  function _interceptValue(native, onSet) {
    Object.defineProperty(native, "value", {
      get() {
        return _nativeValueDescriptor.get.call(this);
      },
      set(v) {
        _nativeValueDescriptor.set.call(this, v);
        onSet();
      },
      configurable: true,
    });
  }

  /**
   * Create the visible trigger <button> that replaces the native input
   * visually. Copies sizing CSS classes from the native input so the button
   * inherits the same form-control sizing as the original field.
   *
   * @param {HTMLInputElement} native
   * @param {boolean}          isReadonly
   * @returns {HTMLButtonElement}
   */
  function _buildTrigger(native, isReadonly) {
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "wf-dp-trigger";
    // Replicate sizing classes
    if (native.classList.contains("form-control-sm")) {
      trigger.classList.add("form-control-sm");
    }
    if (native.classList.contains("form-control")) {
      trigger.classList.add("form-control");
    }
    if (isReadonly) {
      trigger.classList.add("wf-dp-readonly");
      trigger.setAttribute("aria-disabled", "true");
      trigger.setAttribute("tabindex", "-1");
    }
    trigger.setAttribute("aria-haspopup", "dialog");
    trigger.setAttribute("aria-expanded", "false");
    return trigger;
  }

  window._WF_DP.dom = {
    _nativeValueDescriptor,
    _isFocusable,
    _focusBody,
    buildWrapper: _buildWrapper,
    interceptValue: _interceptValue,
    buildTrigger: _buildTrigger,
  };
})();
