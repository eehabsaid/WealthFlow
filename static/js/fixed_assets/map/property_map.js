"use strict";
// Leaflet property map initialization, marker events, and photo upload wiring.
// Part of the fixed_assets module (split from the former monolithic map.js,
// 200-line rule). Do not edit directly.

function initializePropertyMap(lat = 30.0444, lng = 31.2357) {
  if (propertyMap) {
    propertyMap.remove();
    propertyMap = null;
  }

  propertyMap = L.map("propertyMap").setView([lat, lng], 13);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 20,
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
