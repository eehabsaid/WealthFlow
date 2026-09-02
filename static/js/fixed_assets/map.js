"use strict";
// Property map initialization and geocoding
// This file is part of the fixed_assets module. Do not edit directly.

function initializePropertyMap(lat = 30.0444, lng = 31.2357) {
  if (propertyMap) {
    propertyMap.remove();
    propertyMap = null;
  }

  propertyMap = L.map("propertyMap").setView([lat, lng], 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(propertyMap);

  propertyMarker = L.marker([lat, lng], {
    draggable: true,
  }).addTo(propertyMap);

  propertyMarker.on("dragend", function () {
    const p = propertyMarker.getLatLng();

    document.getElementById("re_latitude").value = p.lat.toFixed(6);
    document.getElementById("re_longitude").value = p.lng.toFixed(6);

    reverseGeocode(p.lat, p.lng);
  });

  propertyMap.on("click", function (e) {
    propertyMarker.setLatLng(e.latlng);

    document.getElementById("re_latitude").value = e.latlng.lat.toFixed(6);
    document.getElementById("re_longitude").value = e.latlng.lng.toFixed(6);

    reverseGeocode(e.latlng.lat, e.latlng.lng);
  });

  setTimeout(() => propertyMap.invalidateSize(), 200);

  const uploadBtn = document.getElementById("btnUploadPropertyPhoto");
  const uploadInput = document.getElementById("propertyPhotoInput");

  if (uploadBtn && uploadInput) {
    uploadBtn.onclick = () => uploadInput.click();

    uploadInput.onchange = function () {
      const gallery = document.getElementById("propertyPhotoGallery");

      gallery.innerHTML = "";

      Array.from(this.files).forEach((file) => {
        const reader = new FileReader();

        reader.onload = function (e) {
          gallery.insertAdjacentHTML(
            "beforeend",
            `
                    <div class="col-md-4">

                        <div class="card border-0 shadow-sm">

                            <div class="d-flex justify-content-center align-items-center"
                                style="height:220px; background:var(--bg-secondary);">

                                <img
                                    src="${e.target.result}"
                                    class="img-fluid rounded"
                                    style="
                                        max-width:100%;
                                        max-height:200px;
                                        object-fit:contain;">

                            </div>

                            <div class="card-body p-2 text-center">

                                <div class="small text-truncate">
                                    ${file.name}
                                </div>

                            </div>

                        </div>

                    </div>
                    `
          );
        };

        reader.readAsDataURL(file);
      });
    };
  }
}

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

async function locatePropertyOnMap() {
  const country = document.getElementById("re_country").value.trim();
  const governorate = document.getElementById("re_governorate").value.trim();
  const city = document.getElementById("re_city").value.trim();
  const district = document.getElementById("re_district").value.trim();
  const address = document.getElementById("re_address").value.trim();

  const query = [address, district, city, governorate, country].filter(Boolean).join(", ");

  if (!query) {
    showToast("Please enter an address first.", "warning");
    return;
  }

  showLoading();

  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`
    );

    const results = await response.json();

    if (!results.length) {
      showToast("Address not found.", "warning");
      return;
    }

    const lat = parseFloat(results[0].lat);
    const lng = parseFloat(results[0].lon);

    document.getElementById("re_latitude").value = lat.toFixed(6);
    document.getElementById("re_longitude").value = lng.toFixed(6);

    propertyMap.setView([lat, lng], 17);

    propertyMarker.setLatLng([lat, lng]);
  } catch (err) {
    showToast("Unable to locate address.", "danger");
  } finally {
    hideLoading();
  }
}

async function reverseGeocode(lat, lng) {
  try {
    const currentLang = localStorage.getItem("lang") || "en";

    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&accept-language=${currentLang},en`
    );

    const result = await response.json();

    if (!result.address) return;

    const a = result.address;
    document.getElementById("re_country").value = a.country || "";

    document.getElementById("re_governorate").value = a.state || a.county || "";

    document.getElementById("re_city").value = a.city || a.town || a.village || "";

    document.getElementById("re_district").value =
      a.suburb ||
      a.neighbourhood ||
      a.city_district ||
      a.district ||
      a.municipality ||
      a.hamlet ||
      a.quarter ||
      a.borough ||
      a.village ||
      a.town ||
      a.city ||
      "";

    document.getElementById("re_address").value = result.display_name || "";
  } catch (err) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
}
