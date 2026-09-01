"use strict";

function showModal(html) {
  let el = document.getElementById("globalModal");
  if (!el) {
    el = document.createElement("div");
    el.id = "globalModal";
    el.className = "modal fade modal-dark";
    el.setAttribute("tabindex", "-1");
    document.body.appendChild(el);
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
    if (modal) modal.hide();
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
