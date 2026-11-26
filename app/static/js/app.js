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
})();
