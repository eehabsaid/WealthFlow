function showLoader() {
  const globalLoader = document.getElementById("global-loader");
  if (globalLoader) {
    globalLoader.style.display = "flex";
  } else {
    // Fallback loader if not present
    const loader = document.createElement("div");
    loader.id = "backup-temp-loader";
    loader.style =
      "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;justify-content:center;align-items:center;z-index:9999;color:white;font-size:20px;";
    loader.innerHTML = "<div>Processing ...</div>";
    document.body.appendChild(loader);
  }
}

function hideLoader() {
  const globalLoader = document.getElementById("global-loader");
  if (globalLoader) {
    globalLoader.style.display = "none";
  }
  const tempLoader = document.getElementById("backup-temp-loader");
  if (tempLoader) {
    tempLoader.remove();
  }
}

function showAlert(message, type) {
  if (typeof window.showToast === "function") {
    window.showToast(message, type);
  } else {
    alert(message);
  }
}
