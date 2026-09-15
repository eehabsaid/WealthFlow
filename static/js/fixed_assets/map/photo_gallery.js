"use strict";
// Property photo gallery rendering and deletion.
// Part of the fixed_assets module (split from the former monolithic map.js,
// 200-line rule). Do not edit directly.

function renderPropertyPhotoGallery() {
  const gallery = document.getElementById("propertyPhotoGallery");

  if (!gallery) return;

  gallery.innerHTML = "";

  if (!propertyPhotos || propertyPhotos.length === 0) {
    gallery.innerHTML = `
            <div class="col-12 text-center py-4">
                <i class="bi bi-images"
                   style="font-size:40px;color:var(--text-secondary);opacity:.45;"></i>

                <div class="mt-2"
                     style="color:var(--text-secondary);"
                     data-i18n="no_property_photos">
                    No property photos uploaded
                </div>
            </div>
        `;

    applyTranslations();
    return;
  }

  propertyPhotos.forEach((photo, index) => {
    gallery.innerHTML += `
            <div class="col-md-4 col-lg-3">

                <div class="card border-0 shadow-sm h-100">

                    <img
                        src="${photo.url}"
                        class="card-img-top"
                        style="height:180px;object-fit:cover;">

                        <button
                            type="button"
                            class="btn btn-danger w-100"
                            onclick="removePropertyPhoto(${index})">
                            <i class="bi bi-trash"></i>
                        </button>

                </div>
            </div>
        `;
  });
}

async function removePropertyPhoto(index) {
  const photo = propertyPhotos[index];

  if (!photo) return;

  if (!confirm("Delete this photo?")) return;

  try {
    const response = await fetch(`/api/fixed-assets/${currentEditingAssetId}/photos/${photo.id}/`, {
      method: "DELETE",
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
    });

    if (!response.ok) throw new Error("Failed to delete photo.");

    propertyPhotos.splice(index, 1);

    renderPropertyPhotoGallery();

    showToast("Photo deleted successfully.", "success");
  } catch (err) {
    showToast(err.message, "danger");
  }
}
