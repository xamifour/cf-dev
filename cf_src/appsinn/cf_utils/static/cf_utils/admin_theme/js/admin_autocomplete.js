/**
 * Django admin autocomplete (Select2) extras:
 * - local Select2 on choice/date filter <select class="cf-select2">
 * - navigate on AJAX autocomplete filter change
 */
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function navigateParam(param, value, removeCsv) {
    var params = new URLSearchParams(window.location.search);
    var extra = (removeCsv || "")
      .split(",")
      .map(function (s) {
        return s.trim();
      })
      .filter(Boolean);
    extra.forEach(function (name) {
      params.delete(name);
    });
    if (param) {
      params.delete(param);
      if (value) {
        params.set(param, value);
      }
    }
    var qs = params.toString();
    window.location.search = qs ? qs : "";
  }

  function initLocalSelect2() {
    if (!(window.django && django.jQuery && django.jQuery.fn && django.jQuery.fn.select2)) {
      return;
    }
    var $ = django.jQuery;
    $(".cf-select2").each(function () {
      var $el = $(this);
      if ($el.hasClass("select2-hidden-accessible")) {
        return;
      }
      var placeholder =
        $el.attr("data-placeholder") ||
        ($el.find("option[value='']").text() || "").trim() ||
        "";
      $el.select2({
        width: "100%",
        theme: "admin-autocomplete",
        allowClear: !$el.prop("required"),
        placeholder: placeholder,
        minimumResultsForSearch: 0,
      });
    });
  }

  function bindAutocompleteFilters() {
    document.querySelectorAll("[data-cf-ac-filter]").forEach(function (sel) {
      if (sel.dataset.cfAcBound === "1") {
        return;
      }
      sel.dataset.cfAcBound = "1";
      sel.addEventListener("change", function () {
        navigateParam(
          sel.getAttribute("data-cf-ac-param"),
          sel.value,
          sel.getAttribute("data-cf-ac-remove")
        );
      });
    });
  }

  ready(function () {
    initLocalSelect2();
    bindAutocompleteFilters();
  });
})();
