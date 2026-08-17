/**
 * CF Admin Theme — shell behaviours (gmtisp-style #menu + top account).
 */
(function () {
  "use strict";

  var STORAGE_KEY = "cf.admin.menuCollapsed";

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  function markTheme() {
    document.documentElement.classList.add("cf-admin-theme-root");
    if (document.body && !document.body.classList.contains("cf-admin-theme")) {
      document.body.classList.add("cf-admin-theme");
    }
  }

  function syncHeaderHeight() {
    var header = document.getElementById("header");
    if (!header) {
      return;
    }
    var h = Math.ceil(header.getBoundingClientRect().height) || 56;
    document.documentElement.style.setProperty("--cf-header-h", h + "px");
  }

  /** Left shell menu collapse (sticky #menu, does not reflow content badly). */
  function bindMenuToggle() {
    var container = document.getElementById("container");
    var toggle = document.querySelector("[data-cf-menu-toggle]");
    var backdrop = document.querySelector("[data-cf-menu-backdrop]");
    if (!container || !container.classList.contains("toggle-menu")) {
      return;
    }
    if (container.classList.contains("no-auth")) {
      return;
    }

    function isMobile() {
      return window.matchMedia("(max-width: 900px)").matches;
    }

    function setCollapsed(collapsed) {
      container.classList.toggle("menu-collapsed", collapsed);
      if (isMobile()) {
        container.classList.toggle("menu-open-mobile", !collapsed);
      } else {
        container.classList.remove("menu-open-mobile");
      }
      if (toggle) {
        toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
      }
      try {
        localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
      } catch (e) {
        /* ignore */
      }
    }

    // Restore desktop preference; mobile starts closed.
    var stored = null;
    try {
      stored = localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      stored = null;
    }
    if (isMobile()) {
      setCollapsed(true);
    } else {
      setCollapsed(stored === "1");
    }

    if (toggle) {
      toggle.addEventListener("click", function (ev) {
        ev.preventDefault();
        var collapsed = !container.classList.contains("menu-collapsed");
        if (isMobile()) {
          // On mobile, menu-collapsed means drawer closed.
          var open = container.classList.contains("menu-open-mobile");
          if (open) {
            setCollapsed(true);
          } else {
            container.classList.remove("menu-collapsed");
            container.classList.add("menu-open-mobile");
            toggle.setAttribute("aria-expanded", "true");
          }
        } else {
          setCollapsed(collapsed);
        }
      });
    }

    if (backdrop) {
      backdrop.addEventListener("click", function () {
        if (isMobile()) {
          setCollapsed(true);
        }
      });
    }

    window.addEventListener(
      "resize",
      function () {
        if (isMobile()) {
          if (!container.classList.contains("menu-open-mobile")) {
            container.classList.add("menu-collapsed");
          }
        } else {
          container.classList.remove("menu-open-mobile");
          var pref = null;
          try {
            pref = localStorage.getItem(STORAGE_KEY);
          } catch (e) {
            pref = null;
          }
          setCollapsed(pref === "1");
        }
        syncHeaderHeight();
      },
      { passive: true }
    );
  }

  /** Filter apps in the left menu (replaces Django nav_sidebar filter). */
  function bindMenuFilter() {
    var input = document.querySelector("[data-cf-menu-filter]");
    var root = document.getElementById("cf-menu-apps");
    if (!input || !root) {
      return;
    }
    var rows = [];
    root.querySelectorAll("th[scope=row] a, caption a").forEach(function (a) {
      rows.push({
        title: (a.textContent || "").toLowerCase(),
        node: a.closest("tr") || a.closest(".module") || a.parentElement,
      });
    });
    // Also hide empty modules when filtering model rows
    var modules = Array.prototype.slice.call(root.querySelectorAll(".module"));

    function apply() {
      var q = (input.value || "").toLowerCase().trim();
      rows.forEach(function (r) {
        if (!r.node) {
          return;
        }
        var show = !q || r.title.indexOf(q) !== -1;
        r.node.style.display = show ? "" : "none";
      });
      modules.forEach(function (mod) {
        var any = false;
        mod.querySelectorAll("tr").forEach(function (tr) {
          if (tr.style.display !== "none") {
            any = true;
          }
        });
        // Keep module if caption matches even when rows filtered
        var cap = mod.querySelector("caption a, caption");
        var capText = (cap && cap.textContent ? cap.textContent : "").toLowerCase();
        if (q && capText.indexOf(q) !== -1) {
          mod.style.display = "";
          return;
        }
        if (!q) {
          mod.style.display = "";
          return;
        }
        mod.style.display = any ? "" : "none";
      });
      input.classList.toggle("no-results", !!q && !modules.some(function (m) {
        return m.style.display !== "none";
      }));
    }

    input.addEventListener("input", apply);
    input.addEventListener("keyup", apply);
  }

  function bindAmbientPointer() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }
    var targets = document.querySelectorAll("#header, .cf-dashboard-hero, #menu");
    if (!targets.length) {
      return;
    }
    var raf = null;
    var px = 0.5;
    var py = 0.35;
    function paint() {
      raf = null;
      targets.forEach(function (el) {
        el.style.setProperty("--cf-mx", (px * 100).toFixed(2) + "%");
        el.style.setProperty("--cf-my", (py * 100).toFixed(2) + "%");
      });
    }
    window.addEventListener(
      "pointermove",
      function (ev) {
        var w = window.innerWidth || 1;
        var h = window.innerHeight || 1;
        px = Math.min(1, Math.max(0, ev.clientX / w));
        py = Math.min(1, Math.max(0, ev.clientY / h));
        if (raf == null) {
          raf = window.requestAnimationFrame(paint);
        }
      },
      { passive: true }
    );
  }

  function enhanceMenuCurrent() {
    var root = document.getElementById("cf-menu-apps");
    if (!root) {
      return;
    }
    var path = window.location.pathname;
    root.querySelectorAll("a[href]").forEach(function (a) {
      var href = a.getAttribute("href");
      if (!href || href === "#") {
        return;
      }
      if (path.indexOf(href) === 0 && href.length > 7) {
        a.classList.add("cf-nav-current");
        var row = a.closest("tr, th, td, li");
        if (row) {
          row.classList.add("cf-nav-current-row");
        }
      }
    });
  }

  function bindAccountMenu() {
    var root = document.querySelector("[data-cf-account]");
    if (!root) {
      return;
    }
    var trigger = root.querySelector("[data-cf-account-trigger]");
    var menu = root.querySelector("[data-cf-account-menu]");
    if (!trigger || !menu) {
      return;
    }
    function open() {
      menu.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      root.classList.add("is-open");
    }
    function close() {
      menu.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      root.classList.remove("is-open");
    }
    trigger.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      if (menu.hidden) {
        open();
      } else {
        close();
      }
    });
    document.addEventListener("click", function (ev) {
      if (!root.contains(ev.target)) {
        close();
      }
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        close();
      }
    });
  }

  function bindFilterSelects() {
    document.querySelectorAll("[data-cf-filter-select]").forEach(function (sel) {
      sel.addEventListener("change", function () {
        var val = sel.value;
        if (!val) {
          var all = sel.querySelector('option[value^="?"]') || sel.options[0];
          val = all ? all.value : "";
        }
        if (!val) {
          return;
        }
        if (val.charAt(0) === "?") {
          window.location.search = val;
        } else {
          window.location.href = val;
        }
      });
    });
  }

  /** Horizontal filter strip with left/right arrow controls (no page overflow). */
  function bindFilterScroll() {
    document.querySelectorAll("[data-cf-filter-scroll]").forEach(function (wrap) {
      var track = wrap.querySelector("[data-cf-filter-track]");
      var prev = wrap.querySelector("[data-cf-filter-prev]");
      var next = wrap.querySelector("[data-cf-filter-next]");
      if (!track) {
        return;
      }
      function update() {
        var max = track.scrollWidth - track.clientWidth - 2;
        var left = track.scrollLeft;
        if (prev) {
          prev.disabled = left <= 0;
          prev.classList.toggle("is-disabled", left <= 0);
        }
        if (next) {
          next.disabled = left >= max;
          next.classList.toggle("is-disabled", left >= max);
        }
        wrap.classList.toggle("is-scrollable", max > 4);
      }
      function scrollBy(dir) {
        var amount = Math.max(160, Math.floor(track.clientWidth * 0.7));
        track.scrollBy({ left: dir * amount, behavior: "smooth" });
      }
      if (prev) {
        prev.addEventListener("click", function (ev) {
          ev.preventDefault();
          scrollBy(-1);
        });
      }
      if (next) {
        next.addEventListener("click", function (ev) {
          ev.preventDefault();
          scrollBy(1);
        });
      }
      track.addEventListener("scroll", update, { passive: true });
      window.addEventListener("resize", update, { passive: true });
      update();
      window.setTimeout(update, 50);
    });
  }

  function animateDashboardModules() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }
    if (!document.body.classList.contains("dashboard")) {
      return;
    }
    var modules = document.querySelectorAll(".cf-app-list .module");
    modules.forEach(function (mod, i) {
      mod.style.opacity = "0";
      mod.style.transform = "translateY(8px)";
      mod.style.transition =
        "opacity 0.35s ease " +
        i * 0.04 +
        "s, transform 0.35s ease " +
        i * 0.04 +
        "s";
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () {
          mod.style.opacity = "1";
          mod.style.transform = "none";
        });
      });
    });
  }

  ready(function () {
    markTheme();
    syncHeaderHeight();
    window.addEventListener("resize", syncHeaderHeight, { passive: true });
    bindMenuToggle();
    bindMenuFilter();
    bindAmbientPointer();
    enhanceMenuCurrent();
    bindAccountMenu();
    bindFilterSelects();
    bindFilterScroll();
    animateDashboardModules();
  });
})();
