/* The map of the realms: the pan, the zoom and the card that follows
   the pointer. The picture is drawn by the server; this file only moves
   it around and reads the names out of it. */

(function () {
  "use strict";

  var stage = document.getElementById("realm-map-stage");
  var viewport = document.getElementById("realm-map-viewport");
  if (!stage || !viewport) return;

  var hover = document.getElementById("realm-hover");
  var hoverName = document.getElementById("realm-hover-name");
  var hoverState = document.getElementById("realm-hover-state");
  var hoverLegend = document.getElementById("realm-hover-legend");
  var hoverCastles = document.getElementById("realm-hover-castles");

  var scale = 1;
  var offsetX = 0;
  var offsetY = 0;
  var dragging = false;
  var pointerId = null;
  var startX = 0;
  var startY = 0;
  var originX = 0;
  var originY = 0;

  var MIN_SCALE = 0.6;
  var MAX_SCALE = 4;

  function apply() {
    viewport.style.transform =
      "translate(" + offsetX + "px, " + offsetY + "px) scale(" + scale + ")";
  }

  function clamp(value, low, high) {
    return Math.min(high, Math.max(low, value));
  }

  function zoom(factor) {
    scale = clamp(scale * factor, MIN_SCALE, MAX_SCALE);
    apply();
  }

  function reset() {
    scale = 1;
    offsetX = 0;
    offsetY = 0;
    apply();
  }

  stage.addEventListener("pointerdown", function (event) {
    if (event.target.closest && event.target.closest("button")) return;
    dragging = true;
    pointerId = event.pointerId;
    startX = event.clientX;
    startY = event.clientY;
    originX = offsetX;
    originY = offsetY;
    stage.classList.add("dragging");
    stage.setPointerCapture(event.pointerId);
  });

  stage.addEventListener("pointermove", function (event) {
    if (!dragging || event.pointerId !== pointerId) return;
    offsetX = originX + (event.clientX - startX);
    offsetY = originY + (event.clientY - startY);
    apply();
  });

  function stopDragging(event) {
    if (!dragging) return;
    dragging = false;
    stage.classList.remove("dragging");
    if (pointerId !== null && stage.releasePointerCapture) {
      try {
        stage.releasePointerCapture(pointerId);
      } catch (error) {
        /* the pointer is already gone */
      }
    }
    pointerId = null;
  }

  stage.addEventListener("pointerup", stopDragging);
  stage.addEventListener("pointercancel", stopDragging);

  stage.addEventListener(
    "wheel",
    function (event) {
      event.preventDefault();
      zoom(event.deltaY < 0 ? 1.15 : 0.87);
    },
    { passive: false }
  );

  stage.addEventListener("dblclick", function (event) {
    event.preventDefault();
    zoom(1.3);
  });

  Array.prototype.forEach.call(
    stage.querySelectorAll("[data-map-action]"),
    function (button) {
      button.addEventListener("click", function () {
        var action = button.getAttribute("data-map-action");
        if (action === "zoom-in") zoom(1.25);
        else if (action === "zoom-out") zoom(0.8);
        else reset();
      });
    }
  );

  function showCard(realm, event) {
    if (!hover) return;
    hoverName.textContent = realm.getAttribute("data-name") || "";
    hoverState.textContent = realm.getAttribute("data-state") || "";
    hoverLegend.textContent = realm.getAttribute("data-legend") || "";
    var castles = realm.getAttribute("data-castles") || "0";
    var domain = realm.getAttribute("data-domain") || "";
    hoverCastles.textContent = castles + " · " + domain;
    hover.hidden = false;
    var box = stage.getBoundingClientRect();
    var x = event.clientX - box.left + 14;
    var y = event.clientY - box.top + 14;
    if (x + 260 > box.width) x = Math.max(0, box.width - 260);
    if (y + 140 > box.height) y = Math.max(0, box.height - 140);
    hover.style.left = x + "px";
    hover.style.top = y + "px";
  }

  function hideCard() {
    if (hover) hover.hidden = true;
  }

  Array.prototype.forEach.call(stage.querySelectorAll(".realm"), function (realm) {
    realm.addEventListener("pointerenter", function (event) {
      showCard(realm, event);
    });
    realm.addEventListener("pointermove", function (event) {
      if (hover && !hover.hidden) showCard(realm, event);
    });
    realm.addEventListener("pointerleave", hideCard);
  });

  stage.addEventListener("pointerleave", hideCard);
  apply();
})();
