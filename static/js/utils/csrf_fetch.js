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

  // A 402 {"error": "subscription_required"} means the trial/subscription lapsed: refresh the billing state once
  // (many calls fail together) so the banner shows and the router locks the app to the upgrade page.
  let lastSubscriptionCheck = 0;
  function watchSubscription(promise, url) {
    return promise.then((res) => {
      if (res.status === 402 && isSameOrigin(url)) {
        res
          .clone()
          .json()
          .then((body) => {
            const now = Date.now();
            if (
              body &&
              body.error === "subscription_required" &&
              now - lastSubscriptionCheck > 5000
            ) {
              lastSubscriptionCheck = now;
              if (typeof window.checkBillingStatus === "function") window.checkBillingStatus();
            }
          })
          .catch(() => {});
      }
      return res;
    });
  }

  window.fetch = function (input, init) {
    const options = init || {};
    const isRequest = typeof Request !== "undefined" && input instanceof Request;
    const method = options.method || (isRequest ? input.method : "GET");
    const url = isRequest ? input.url : String(input);
    const token = getCookie("csrftoken");

    if (SAFE_METHODS.test(method) || !token || !isSameOrigin(url)) {
      return watchSubscription(nativeFetch(input, init), url);
    }

    const headers = new Headers(options.headers || (isRequest ? input.headers : undefined));
    if (!headers.get("X-CSRFToken")) {
      headers.set("X-CSRFToken", token);
    }
    return watchSubscription(nativeFetch(input, Object.assign({}, options, { headers })), url);
  };
})();
