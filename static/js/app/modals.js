"use strict";

// Bootstrap silently ignores show()/hide() while a transition is running. "opening" = show animation in progress,
// "closing" = hide animation in progress. (_isTransitioning/_isShown are Bootstrap 5's own state flags.)
function _modalPhase(modal) {
  if (!modal || !modal._isTransitioning) return "idle";
  return modal._isShown ? "opening" : "closing";
}

function showModal(html) {
  let el = document.getElementById("globalModal");
  if (!el) {
    el = document.createElement("div");
    el.id = "globalModal";
    el.className = "modal fade modal-dark";
    el.setAttribute("tabindex", "-1");
    document.body.appendChild(el);
  }

  // Reopened while the previous one is still fading out: Bootstrap would drop show(), so wait for it to finish.
  if (_modalPhase(bootstrap.Modal.getInstance(el)) === "closing") {
    el.addEventListener("hidden.bs.modal", () => setTimeout(() => showModal(html), 0), {
      once: true,
    });
    return;
  }

  // Reset any legacy inline padding on body before showing modal
  document.body.style.paddingRight = "";
  document.body.style.overflow = "";

  el.innerHTML = `
        <div class="modal-dialog modal-xl modal-dialog-scrollable">
            <div class="modal-content">${html}</div>
        </div>`;

  let modal = bootstrap.Modal.getInstance(el);
  if (!modal) {
    modal = new bootstrap.Modal(el, {
      backdrop: "static",
      keyboard: false,
    });
  }
  modal.show();
}

function closeModal() {
  const el = document.getElementById("globalModal");
  if (el) {
    const modal = bootstrap.Modal.getInstance(el);
    if (modal) {
      // Dispose once Bootstrap's own hide transition finishes, not
      // immediately — disposing mid-transition would cut the fade short.
      // Without this, the instance is left in a "hiding" state and the
      // next showModal()'s modal.show() is silently ignored (documented
      // shared-modal race: #globalModal is reused across ~29 files).
      el.addEventListener(
        "hidden.bs.modal",
        () => {
          const stale = bootstrap.Modal.getInstance(el);
          if (stale) stale.dispose();
        },
        { once: true }
      );
      // Close clicked while the show animation is still running: hide() would be ignored and the modal would
      // stay open, so finish the close as soon as it has finished opening.
      if (_modalPhase(modal) === "opening") {
        el.addEventListener("shown.bs.modal", () => modal.hide(), { once: true });
      }
      modal.hide();
    }
  }
  document.body.style.paddingRight = "";
  document.body.style.overflow = "";
}

// ── Global Modal Lifecycle Protection against Body Padding Accumulation ──
document.addEventListener("show.bs.modal", function () {
  document.body.style.paddingRight = "";
});

document.addEventListener("hidden.bs.modal", function () {
  if (!document.querySelector(".modal.show")) {
    document.body.classList.remove("modal-open");
    document.body.style.paddingRight = "";
    document.body.style.overflow = "";
  }
});
