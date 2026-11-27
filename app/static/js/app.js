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
      event.preventDefault();
      if (link) {
        link.click();
      } else {
        window.location.href = "/tasks/new";
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

/* The CSRF token of the page: the hidden field of a form, or the cookie. */
function csrfToken() {
  const input = document.querySelector("input[name='csrf_token']");
  if (input) return input.value;
  const match = document.cookie.match(/(?:^|;\s*)varagh_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}
window.csrfToken = csrfToken;

/* The reason of a time entry is required when the kind is overtime. */
function varaghToggleOvertimeReason() {
  var select = document.getElementById("kind");
  var reason = document.getElementById("reason");
  if (!select || !reason) return;
  var apply = function () {
    reason.required = select.value === "overtime";
  };
  select.addEventListener("change", apply);
  apply();
}
document.addEventListener("DOMContentLoaded", varaghToggleOvertimeReason);

/* A form that is built in the browser and sent right away. It keeps the
   checkboxes of a list out of the page, so a list may hold its own forms. */
function varaghPost(url, fields) {
  var form = document.createElement("form");
  form.method = "post";
  form.action = url;
  var token = document.createElement("input");
  token.type = "hidden";
  token.name = "csrf_token";
  token.value = csrfToken();
  form.appendChild(token);
  Object.keys(fields || {}).forEach(function (name) {
    var values = Array.isArray(fields[name]) ? fields[name] : [fields[name]];
    values.forEach(function (value) {
      var input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = value;
      form.appendChild(input);
    });
  });
  document.body.appendChild(form);
  form.submit();
}
window.varaghPost = varaghPost;

/* The selection of a list: the checkboxes of the rows and the actions of the
   page. The ids are the values of the checkboxes, as strings. */
function varaghSelection(ids) {
  return {
    selected: [],
    /* The ids are the values of the checkboxes: strings. */
    ids: (ids || []).map(String),
    toggleAll(value) {
      this.selected = value ? this.ids.slice() : [];
    },
    confirmMessage(attribute) {
      var root = this.$root;
      if (!root || !root.getAttribute) return "";
      return root.getAttribute(attribute) || "";
    },
    deleteAll(url, field) {
      if (!this.selected.length) return;
      var message = this.confirmMessage("data-confirm");
      if (message && !window.confirm(message)) return;
      var payload = {};
      payload[field] = this.selected.slice();
      varaghPost(url, payload);
    },
    deleteOne(url) {
      var message = this.confirmMessage("data-confirm-one");
      if (message && !window.confirm(message)) return;
      varaghPost(url, {});
    },
  };
}
window.varaghSelection = varaghSelection;

/* Alpine calls this event before it evaluates the first expression. */
document.addEventListener("alpine:init", function () {
  window.varaghSelection = varaghSelection;
});

/* A form may ask for a confirmation before it is sent. */
document.addEventListener("submit", function (event) {
  const form = event.target;
  if (!form || !form.getAttribute) return;
  const message = form.getAttribute("data-confirm");
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});

/* Charts of the AI answers. The data comes from the server: the model only
   chooses which series of the database it wants to show. */
(function () {
  const PALETTE = ["#2f6f5e", "#c2703d", "#4a6fa5", "#8a6fa5", "#b0553f", "#5a8a4a"];
  const ROUND_TYPES = ["doughnut", "pie"];

  function varaghRenderChart(canvas, spec) {
    if (!canvas || !spec || typeof Chart === "undefined") return null;
    const round = ROUND_TYPES.indexOf(spec.type) !== -1;
    return new Chart(canvas, {
      type: spec.type || "bar",
      data: {
        labels: spec.labels || [],
        datasets: [
          {
            label: spec.unit || "",
            data: spec.values || [],
            backgroundColor: round ? PALETTE : PALETTE[0],
            borderColor: round ? "#ffffff" : "transparent",
            borderWidth: round ? 2 : 0,
            borderRadius: round ? 0 : 6,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: round } },
        scales: round ? {} : { y: { beginAtZero: true } },
      },
    });
  }

  window.varaghRenderChart = varaghRenderChart;

  function renderAll(root) {
    const canvases = (root || document).querySelectorAll("canvas[data-chart]");
    canvases.forEach(function (canvas) {
      if (canvas.getAttribute("data-chart-ready") === "1") return;
      try {
        const spec = JSON.parse(canvas.getAttribute("data-chart"));
        if (varaghRenderChart(canvas, spec)) {
          canvas.setAttribute("data-chart-ready", "1");
        }
      } catch (error) {
        /* a broken chart must never break the page */
      }
    });
  }

  window.varaghRenderCharts = renderAll;

  document.addEventListener("DOMContentLoaded", function () {
    renderAll(document);
  });
})();
