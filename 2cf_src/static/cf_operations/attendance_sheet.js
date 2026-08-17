/* Pin CODE + CENTRE NAME while the rest of the attendance sheet scrolls. */
(function () {
  "use strict";

  function pinColumns() {
    var table = document.querySelector("table.attendance-sheet");
    if (!table) {
      return;
    }
    var header = table.querySelector("tr.sheet-col-header");
    if (!header || header.children.length < 2) {
      return;
    }
    var first = header.children[0];
    var width = Math.ceil(first.getBoundingClientRect().width);
    if (width < 40) {
      width = 72;
    }
    table.style.setProperty("--sheet-pin-1", width + "px");
    table.classList.add("is-pinned");
  }

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  ready(function () {
    pinColumns();
    window.addEventListener("resize", pinColumns, { passive: true });
  });
})();
