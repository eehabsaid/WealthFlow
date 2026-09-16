"use strict";
// Uploads any pending property photos selected in the form after a
// successful fixed-asset save.
// Part of the fixed_assets module (split from the former monolithic
// save_asset.js, 200-line rule). Do not edit directly.

async function uploadPendingFixedAssetPhotos(assetId) {
  const files = document.getElementById("propertyPhotoInput").files;

  if (files.length > 0) {
    for (const file of files) {
      const formData = new FormData();
      formData.append("photos", file);

      const uploadResponse = await fetch(`/api/fixed-assets/${assetId}/photos/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCsrfToken(),
        },
        body: formData,
      });

      if (!uploadResponse.ok) throw new Error("Failed to upload property photo.");

      const uploadedPhoto = await uploadResponse.json();
      if (Array.isArray(uploadedPhoto)) {
        propertyPhotos.push(...uploadedPhoto);
      } else if (uploadedPhoto) {
        propertyPhotos.push(uploadedPhoto);
      }
    }

    renderPropertyPhotoGallery();
    document.getElementById("propertyPhotoInput").value = "";
  }
}
