/* Varagh — small progressive-enhancement layer. Works without any CDN. */
(function () {
  "use strict";

  const root = document.documentElement;

  window.varaghToggleTheme = function () {
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("varagh-theme", next);
  };

  function isTypingTarget(element) {
    if (!element) return false;
    const tag = element.tagName;
    return (
      tag === "INPUT" ||
      tag === "TEXTAREA" ||
      tag === "SELECT" ||
      element.isContentEditable
    );
  }

  document.addEventListener("keydown", function (event) {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (isTypingTarget(event.target)) return;

    if (event.key === "/") {
      const input = document.querySelector(".quick-add input[name='title']");
      if (input) {
        event.preventDefault();
        input.focus();
        input.select();
      }
    } else if (event.key === "n") {
      const link = document.querySelector("[data-shortcut='new-task']");
      if (link) {
        event.preventDefault();
        link.click();
      }
    }
  });

  function tickTimer() {
    const el = document.getElementById("timer-elapsed");
    if (!el) return;
    const started = Date.parse(el.dataset.started);
    if (Number.isNaN(started)) return;
    const seconds = Math.max(0, Math.floor((Date.now() - started) / 1000));
    const hh = String(Math.floor(seconds / 3600)).padStart(2, "0");
    const mm = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
    const ss = String(seconds % 60).padStart(2, "0");
    el.textContent = hh + ":" + mm + ":" + ss;
  }

  if (document.getElementById("timer-elapsed")) {
    tickTimer();
    setInterval(tickTimer, 1000);
  }

  /* ------------------------------------------------------------------
   * Browser notifications.
   *
   * The container cannot reach the host operating system, so the worker
   * queues the notifications in the database and this page polls for them
   * and raises the real OS notification through the Web Notifications API.
   * ------------------------------------------------------------------ */
  const POLL_INTERVAL_MS = 45000;

  /* Register the service worker so the app can be installed as a PWA. */
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {
        /* the app works without the service worker */
      });
    });
  }

  function csrfToken() {
    const input = document.querySelector("input[name='csrf_token']");
    return input ? input.value : "";
  }

  function markRead(id) {
    return fetch("/api/notifications/" + id + "/read", {
      method: "POST",
      headers: { "X-CSRF-Token": csrfToken() },
    });
  }

  function showNotification(item) {
    if (!("Notification" in window)) return;
    if (window.Notification.permission === "granted") {
      new Notification(item.title, { body: item.body, tag: "varagh-" + item.id });
    }
    markRead(item.id);
  }

  function pollNotifications() {
    fetch("/api/notifications/due", { headers: { Accept: "application/json" } })
      .then(function (response) {
        return response.ok ? response.json() : { notifications: [] };
      })
      .then(function (data) {
        (data.notifications || []).forEach(showNotification);
      })
      .catch(function () {
        /* offline: try again on the next tick */
      });
  }

  const notifyButton = document.getElementById("enable-notifications");
  if (notifyButton && "Notification" in window) {
    notifyButton.addEventListener("click", function () {
      window.Notification.requestPermission().then(function () {
        pollNotifications();
      });
    });
  }

  if ("Notification" in window) {
    setInterval(pollNotifications, POLL_INTERVAL_MS);
  }
})();
