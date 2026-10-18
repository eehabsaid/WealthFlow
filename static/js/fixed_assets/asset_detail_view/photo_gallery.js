"use strict";
// Asset Details > Photos: one frame, previous/next arrows (direction-aware), thumbnails.
// Shared by the real-estate and non-real-estate detail modals.

const ASSET_PHOTO_ICON_PREV =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>';
const ASSET_PHOTO_ICON_NEXT =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>';

function buildAssetPhotoGalleryHtml(photos) {
  if (!photos.length) {
    return `<div id="assetMainPhotoContainer" class="asset-main-photo-container mb-3"><div class="text-center" data-i18n="no_property_photos">No photos available</div></div>`;
  }
  const many = photos.length > 1;
  const arrows = many
    ? `<button type="button" class="asset-photo-nav asset-photo-prev" data-i18n-title="previous_photo" title="Previous photo">${ASSET_PHOTO_ICON_PREV}</button>
       <button type="button" class="asset-photo-nav asset-photo-next" data-i18n-title="next_photo" title="Next photo">${ASSET_PHOTO_ICON_NEXT}</button>
       <span class="asset-photo-counter" id="assetPhotoCounter">1 / ${photos.length}</span>`
    : "";
  const thumbs = many
    ? photos
        .map(
          (photo, index) =>
            `<button type="button" class="btn btn-sm asset-photo-thumbnail p-0${index === 0 ? " active" : ""}" data-index="${index}" data-url="${photo.url}" aria-label="Photo ${index + 1}"><img src="${photo.url}" alt="Thumbnail ${index + 1}" /></button>`
        )
        .join("")
    : "";
  return `<div id="assetMainPhotoContainer" class="asset-main-photo-container asset-photo-gallery mb-3" tabindex="0">
      <img id="assetMainPhoto" src="${photos[0].url}" alt="Asset photo" class="img-fluid" style="cursor:pointer;" />
      ${arrows}
    </div>
    ${many ? `<div class="asset-photo-grid">${thumbs}</div>` : ""}`;
}

// Size the frame so the whole image is visible and the modal body does not scroll.
function fitAssetPhotoFrame() {
  const frame = document.getElementById("assetMainPhotoContainer");
  const body = frame?.closest(".asset-modal-body");
  if (!frame || !body || !frame.offsetParent) return;
  const grid = document.querySelector(".asset-photo-grid");
  const frameTop =
    frame.getBoundingClientRect().top - body.getBoundingClientRect().top + body.scrollTop;
  const gridH = grid ? grid.offsetHeight + 16 : 0;
  const reserve = 16 + 24 + 20; // frame margin + card padding + breathing room
  const avail = body.clientHeight - frameTop - gridH - reserve;
  frame.style.height = `${Math.max(140, Math.floor(avail))}px`;
}

function initAssetPhotoGallery(photos) {
  const main = document.getElementById("assetMainPhoto");
  const frame = document.getElementById("assetMainPhotoContainer");
  if (!main || !frame) return;
  const thumbs = Array.from(document.querySelectorAll(".asset-photo-thumbnail"));
  const counter = document.getElementById("assetPhotoCounter");
  let current = 0;
  frame.querySelectorAll(".asset-photo-nav").forEach((b) => b.setAttribute("aria-label", b.title));
  const isRtl = () => getComputedStyle(frame).direction === "rtl";

  function show(index) {
    current = (index + photos.length) % photos.length;
    main.src = photos[current].url;
    if (counter) counter.textContent = `${current + 1} / ${photos.length}`;
    thumbs.forEach((t, i) => t.classList.toggle("active", i === current));
    thumbs[current]?.scrollIntoView?.({ block: "nearest", inline: "center" });
  }

  thumbs.forEach((thumb) =>
    thumb.addEventListener("click", () => show(Number(thumb.dataset.index)))
  );
  frame.querySelector(".asset-photo-prev")?.addEventListener("click", (e) => {
    e.stopPropagation();
    show(current - 1);
  });
  frame.querySelector(".asset-photo-next")?.addEventListener("click", (e) => {
    e.stopPropagation();
    show(current + 1);
  });

  if (photos.length > 1) {
    frame.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      let step = e.key === "ArrowRight" ? 1 : -1;
      if (isRtl()) step = -step;
      show(current + step);
      e.preventDefault();
    });
    let startX = null;
    frame.addEventListener("touchstart", (e) => (startX = e.touches[0].clientX), { passive: true });
    frame.addEventListener("touchend", (e) => {
      if (startX === null) return;
      const dx = e.changedTouches[0].clientX - startX;
      startX = null;
      if (Math.abs(dx) < 40) return;
      let step = dx < 0 ? 1 : -1;
      if (isRtl()) step = -step;
      show(current + step);
    });
  }

  const modal = frame.closest(".modal");
  document.getElementById("asset-photos-tab")?.addEventListener("shown.bs.tab", fitAssetPhotoFrame);
  window.addEventListener("resize", fitAssetPhotoFrame);
  modal?.addEventListener(
    "hidden.bs.modal",
    () => window.removeEventListener("resize", fitAssetPhotoFrame),
    { once: true }
  );
  setTimeout(fitAssetPhotoFrame, 0);
}
