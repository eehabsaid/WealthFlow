"use strict";
// Global CSRF protection for the SPA: every same-origin unsafe fetch()
// (POST/PUT/PATCH/DELETE) automatically carries the X-CSRFToken header read
// from the csrftoken cookie. Loaded first so all later scripts are covered.
// Django's CsrfViewMiddleware rejects those requests without it.

(function () {
  const SAFE_METHODS = /^(GET|HEAD|OPTIONS|TRACE)$/i;
  const nativeFetch = window.fetch.bind(window);

  function getCookie(name) {
    const parts = (document.cookie || "").split(";");
    for (let i = 0; i < parts.length; i += 1) {
      const part = parts[i].trim();
      if (part.startsWith(`${name}=`)) {
        return decodeURIComponent(part.substring(name.length + 1));
      }
    }
    return "";
  }

  function isSameOrigin(url) {
    try {
      return new URL(url, window.location.href).origin === window.location.origin;
    } catch (err) {
      return false;
    }
  }

  window.wfGetCsrfToken = () => getCookie("csrftoken");

  window.fetch = function (input, init) {
    const options = init || {};
    const isRequest = typeof Request !== "undefined" && input instanceof Request;
    const method = options.method || (isRequest ? input.method : "GET");
    const url = isRequest ? input.url : String(input);
    const token = getCookie("csrftoken");

    if (SAFE_METHODS.test(method) || !token || !isSameOrigin(url)) {
      return nativeFetch(input, init);
    }

    const headers = new Headers(options.headers || (isRequest ? input.headers : undefined));
    if (!headers.get("X-CSRFToken")) {
      headers.set("X-CSRFToken", token);
    }
    return nativeFetch(input, Object.assign({}, options, { headers }));
  };
})();
