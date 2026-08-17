/* cf-dev/cf_src/static/cf_users/portal.js */

(function () {
  "use strict";

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function qsa(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function initNav() {
    var nav = qs("[data-c-nav]");
    if (!nav) {
      return;
    }

    var exploreTrigger = qs("[data-c-explore-trigger]", nav);
    var explorePanel = qs("[data-c-explore-panel]", nav);
    var menuToggle = qs("[data-c-menu-toggle]", nav);
    var mobileDrawer = qs("[data-c-mobile-drawer]", nav);
    var backdrop = qs("[data-c-nav-backdrop]", nav);
    var mobileSearch = qs("[data-c-mobile-search]", nav);

    function setExpanded(el, open) {
      if (!el) {
        return;
      }
      el.setAttribute("aria-expanded", open ? "true" : "false");
    }

    function setHidden(el, hidden) {
      if (!el) {
        return;
      }
      if (hidden) {
        el.setAttribute("hidden", "");
        el.setAttribute("aria-hidden", "true");
      } else {
        el.removeAttribute("hidden");
        el.setAttribute("aria-hidden", "false");
      }
    }

    function closeExplore() {
      nav.classList.remove("is-explore-open");
      setExpanded(exploreTrigger, false);
      setHidden(explorePanel, true);
    }

    function openExplore() {
      closeMobile();
      nav.classList.add("is-explore-open");
      setExpanded(exploreTrigger, true);
      setHidden(explorePanel, false);
    }

    function toggleExplore() {
      if (nav.classList.contains("is-explore-open")) {
        closeExplore();
      } else {
        openExplore();
      }
    }

    function closeMobile() {
      nav.classList.remove("is-mobile-open");
      setExpanded(menuToggle, false);
      setHidden(mobileDrawer, true);
      setHidden(backdrop, true);
      if (menuToggle) {
        menuToggle.setAttribute(
          "aria-label",
          menuToggle.dataset.labelOpen || "Open menu"
        );
      }
      document.body.classList.remove("c-nav-locked");
      if (mobileSearch) {
        mobileSearch.value = "";
        filterMobileLinks("");
      }
    }

    function openMobile() {
      closeExplore();
      nav.classList.add("is-mobile-open");
      setExpanded(menuToggle, true);
      setHidden(mobileDrawer, false);
      setHidden(backdrop, false);
      if (menuToggle) {
        menuToggle.setAttribute(
          "aria-label",
          menuToggle.dataset.labelClose || "Close menu"
        );
      }
      document.body.classList.add("c-nav-locked");
      // Focus search for quick access on small screens.
      window.setTimeout(function () {
        if (mobileSearch) {
          mobileSearch.focus();
        }
      }, 50);
    }

    function toggleMobile(event) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      if (nav.classList.contains("is-mobile-open")) {
        closeMobile();
      } else {
        openMobile();
      }
    }

    function filterMobileLinks(query) {
      var q = (query || "").trim().toLowerCase();
      qsa(".c-mobile-nav a", nav).forEach(function (link) {
        var label = (
          link.getAttribute("data-c-search-label") ||
          link.textContent ||
          ""
        ).toLowerCase();
        var match = !q || label.indexOf(q) !== -1;
        link.classList.toggle("is-filtered-out", !match);
      });
      qsa(".c-mobile-section-label", nav).forEach(function (labelEl) {
        // Hide section labels when every following link until next label is filtered.
        var next = labelEl.nextElementSibling;
        var anyVisible = false;
        while (next && !next.classList.contains("c-mobile-section-label")) {
          if (
            next.matches("a") &&
            !next.classList.contains("is-filtered-out")
          ) {
            anyVisible = true;
            break;
          }
          next = next.nextElementSibling;
        }
        labelEl.classList.toggle("is-filtered-out", q && !anyVisible);
      });
    }

    if (exploreTrigger) {
      exploreTrigger.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        toggleExplore();
      });
    }

    if (menuToggle) {
      menuToggle.dataset.labelOpen =
        menuToggle.getAttribute("aria-label") || "Open menu";
      menuToggle.dataset.labelClose = "Close menu";
      menuToggle.addEventListener("click", toggleMobile);
    }

    if (backdrop) {
      backdrop.addEventListener("click", function (event) {
        event.preventDefault();
        closeMobile();
        closeExplore();
      });
    }

    qsa("[data-c-close-menu]", nav).forEach(function (link) {
      link.addEventListener("click", function () {
        closeMobile();
        closeExplore();
      });
    });

    if (explorePanel) {
      qsa("a", explorePanel).forEach(function (link) {
        link.addEventListener("click", function () {
          closeExplore();
        });
      });
    }

    if (mobileSearch) {
      mobileSearch.addEventListener("input", function () {
        filterMobileLinks(mobileSearch.value);
      });
      // Keep typing/focus from bubbling to document click handlers.
      mobileSearch.addEventListener("click", function (event) {
        event.stopPropagation();
      });
    }

    // Account actions must remain clickable; stop backdrop-level close logic.
    if (mobileDrawer) {
      mobileDrawer.addEventListener("click", function (event) {
        event.stopPropagation();
      });
    }

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeExplore();
        closeMobile();
      }
    });

    document.addEventListener("click", function (event) {
      if (nav.classList.contains("is-explore-open")) {
        if (!nav.contains(event.target)) {
          closeExplore();
        }
      }
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth > 1024) {
        closeMobile();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initNav);
  } else {
    initNav();
  }
})();
