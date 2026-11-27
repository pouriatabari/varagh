/* The drawing of the board.

   The user draws on a canvas with the pointer — a mouse, a pen or a finger.
   The strokes are kept in a list, so the undo can draw them again, and the
   save sends the canvas as a PNG to the server, which puts it on the board. */

(function () {
  const area = document.getElementById("drawing-area");
  if (!area) return;

  const canvas = area.querySelector("canvas");
  if (!canvas || !canvas.getContext) return;
  const context = canvas.getContext("2d");

  const colors = area.querySelectorAll("[data-drawing-color]");
  const widths = area.querySelectorAll("[data-drawing-width]");
  const undoButton = area.querySelector("[data-drawing-undo]");
  const clearButton = area.querySelector("[data-drawing-clear]");
  const saveButton = area.querySelector("[data-drawing-save]");
  const status = area.querySelector("[data-drawing-status]");

  let color = "#e05a4f";
  let width = 4;
  let strokes = [];
  let current = null;

  function resize() {
    /* The canvas follows the width of the page, and the lines stay sharp on
       a screen with many pixels per inch. */
    const ratio = window.devicePixelRatio || 1;
    const box = area.getBoundingClientRect();
    const height = Math.max(220, Math.round(box.width * 0.42));
    canvas.width = Math.round(box.width * ratio);
    canvas.height = Math.round(height * ratio);
    canvas.style.width = box.width + "px";
    canvas.style.height = height + "px";
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.lineCap = "round";
    context.lineJoin = "round";
    redraw();
  }

  function redraw() {
    context.clearRect(0, 0, canvas.width, canvas.height);
    for (const stroke of strokes) {
      context.strokeStyle = stroke.color;
      context.lineWidth = stroke.width;
      context.beginPath();
      for (let index = 0; index < stroke.points.length; index += 1) {
        const point = stroke.points[index];
        if (index === 0) {
          context.moveTo(point[0], point[1]);
        } else {
          context.lineTo(point[0], point[1]);
        }
      }
      context.stroke();
    }
  }

  function pointOf(event) {
    const box = canvas.getBoundingClientRect();
    return [event.clientX - box.left, event.clientY - box.top];
  }

  canvas.addEventListener("pointerdown", function (event) {
    event.preventDefault();
    canvas.setPointerCapture(event.pointerId);
    current = { color: color, width: width, points: [pointOf(event)] };
    strokes.push(current);
    redraw();
  });

  canvas.addEventListener("pointermove", function (event) {
    if (!current) return;
    const point = pointOf(event);
    const last = current.points[current.points.length - 1];
    /* Only the points that really moved are kept: a slow mouse sends a lot
       of events, and the stroke would grow for nothing. */
    if (Math.abs(point[0] - last[0]) + Math.abs(point[1] - last[1]) < 1) return;
    current.points.push(point);
    redraw();
  });

  function finish() {
    current = null;
  }

  canvas.addEventListener("pointerup", finish);
  canvas.addEventListener("pointercancel", finish);
  canvas.addEventListener("pointerleave", finish);

  colors.forEach(function (button) {
    button.addEventListener("click", function () {
      color = button.dataset.drawingColor;
      colors.forEach(function (other) {
        other.classList.toggle("active", other === button);
      });
    });
  });

  widths.forEach(function (button) {
    button.addEventListener("click", function () {
      width = Number(button.dataset.drawingWidth) || 4;
      widths.forEach(function (other) {
        other.classList.toggle("active", other === button);
      });
    });
  });

  if (undoButton) {
    undoButton.addEventListener("click", function () {
      strokes.pop();
      redraw();
    });
  }

  if (clearButton) {
    clearButton.addEventListener("click", function () {
      strokes = [];
      redraw();
    });
  }

  if (saveButton) {
    saveButton.addEventListener("click", function () {
      if (!strokes.length) {
        if (status) status.textContent = area.dataset.drawingEmpty || "";
        return;
      }
      const form = document.createElement("form");
      form.method = "post";
      form.action = area.dataset.drawingUrl || "";
      form.innerHTML =
        '<input name="csrf_token" value="' + (area.dataset.csrfToken || "") + '">' +
        '<input name="data_url" value="' + canvas.toDataURL("image/png") + '">';
      document.body.appendChild(form);
      form.submit();
    });
  }

  window.addEventListener("resize", resize);
  resize();
})();
