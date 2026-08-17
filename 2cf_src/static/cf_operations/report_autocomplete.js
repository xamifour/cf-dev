/* Searchable autocomplete for Generate attendance report scope <select>s. */
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function parentValues(select) {
    var names = (select.getAttribute("data-combo-parents") || "")
      .split(",")
      .map(function (s) {
        return s.trim();
      })
      .filter(Boolean);
    var values = {};
    names.forEach(function (name) {
      var el = document.getElementById("id_" + name);
      values[name] = el ? String(el.value || "") : "";
    });
    return values;
  }

  function optionMatchesParents(option, parents) {
    if (!option.value) {
      return true;
    }
    for (var key in parents) {
      if (!Object.prototype.hasOwnProperty.call(parents, key)) {
        continue;
      }
      var wanted = parents[key];
      if (!wanted) {
        continue;
      }
      var got = option.getAttribute("data-" + key);
      if (got && String(got) !== wanted) {
        return false;
      }
    }
    return true;
  }

  function selectedLabel(select) {
    var opt = select.options[select.selectedIndex];
    return opt ? (opt.textContent || "").trim() : "";
  }

  function enhance(select) {
    if (select.dataset.comboReady === "1") {
      return;
    }
    select.dataset.comboReady = "1";

    var wrap = document.createElement("div");
    wrap.className = "cf-combo";
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);
    select.classList.add("cf-combo-source");
    select.setAttribute("tabindex", "-1");
    select.setAttribute("aria-hidden", "true");

    var input = document.createElement("input");
    input.type = "text";
    input.className = "cf-combo-input";
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("autocomplete", "off");
    input.setAttribute("spellcheck", "false");
    input.placeholder =
      select.getAttribute("data-combo-placeholder") ||
      (select.options[0] ? select.options[0].textContent.trim() : "");
    if (select.id) {
      input.id = select.id + "_combo";
      var label = document.querySelector('label[for="' + select.id + '"]');
      if (label) {
        label.setAttribute("for", input.id);
      }
    }
    input.value = selectedLabel(select);

    var list = document.createElement("ul");
    list.className = "cf-combo-list";
    list.hidden = true;
    list.setAttribute("role", "listbox");
    var listId = (select.id || "combo") + "_list";
    list.id = listId;
    input.setAttribute("aria-controls", listId);

    wrap.appendChild(input);
    wrap.appendChild(list);

    var activeIndex = -1;

    function visibleOptions(query) {
      var q = (query || "").trim().toLowerCase();
      var parents = parentValues(select);
      var out = [];
      for (var i = 0; i < select.options.length; i++) {
        var opt = select.options[i];
        if (!optionMatchesParents(opt, parents)) {
          continue;
        }
        var text = (opt.textContent || "").trim();
        if (q && text.toLowerCase().indexOf(q) === -1) {
          continue;
        }
        out.push({ option: opt, text: text, index: i });
      }
      return out;
    }

    function close() {
      list.hidden = true;
      list.innerHTML = "";
      input.setAttribute("aria-expanded", "false");
      activeIndex = -1;
    }

    function setActive(items, idx) {
      var nodes = list.querySelectorAll("[role='option']");
      nodes.forEach(function (n) {
        n.classList.remove("is-active");
      });
      if (idx < 0 || idx >= nodes.length) {
        activeIndex = -1;
        return;
      }
      activeIndex = idx;
      nodes[idx].classList.add("is-active");
      nodes[idx].scrollIntoView({ block: "nearest" });
    }

    function choose(item) {
      select.value = item.option.value;
      input.value = item.text;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      close();
    }

    function open(query) {
      var items = visibleOptions(query);
      list.innerHTML = "";
      if (!items.length) {
        var empty = document.createElement("li");
        empty.className = "cf-combo-empty";
        empty.textContent = "No matches";
        list.appendChild(empty);
        list.hidden = false;
        input.setAttribute("aria-expanded", "true");
        activeIndex = -1;
        return;
      }
      items.forEach(function (item, i) {
        var li = document.createElement("li");
        li.setAttribute("role", "option");
        li.className = "cf-combo-option";
        if (item.option.value === select.value) {
          li.classList.add("is-selected");
        }
        li.textContent = item.text;
        li.addEventListener("mousedown", function (ev) {
          ev.preventDefault();
          choose(item);
        });
        list.appendChild(li);
        if (item.option.value === select.value) {
          activeIndex = i;
        }
      });
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
      if (activeIndex >= 0) {
        setActive(items, activeIndex);
      }
    }

    input.addEventListener("focus", function () {
      open(input.value === selectedLabel(select) ? "" : input.value);
    });
    input.addEventListener("input", function () {
      open(input.value);
    });
    input.addEventListener("keydown", function (ev) {
      var items = visibleOptions(
        input.value === selectedLabel(select) ? "" : input.value
      );
      if (ev.key === "ArrowDown") {
        ev.preventDefault();
        if (list.hidden) {
          open("");
        } else {
          setActive(items, Math.min(items.length - 1, activeIndex + 1));
        }
      } else if (ev.key === "ArrowUp") {
        ev.preventDefault();
        setActive(items, Math.max(0, activeIndex - 1));
      } else if (ev.key === "Enter") {
        if (!list.hidden && activeIndex >= 0 && items[activeIndex]) {
          ev.preventDefault();
          choose(items[activeIndex]);
        }
      } else if (ev.key === "Escape") {
        ev.preventDefault();
        input.value = selectedLabel(select);
        close();
      }
    });
    input.addEventListener("blur", function () {
      window.setTimeout(function () {
        if (!wrap.contains(document.activeElement)) {
          input.value = selectedLabel(select);
          close();
        }
      }, 120);
    });

    document.addEventListener("click", function (ev) {
      if (!wrap.contains(ev.target)) {
        close();
      }
    });

    select.addEventListener("change", function () {
      input.value = selectedLabel(select);
    });
  }

  function syncChildren(changed) {
    var id = changed.id || "";
    if (id.indexOf("id_") !== 0) {
      return;
    }
    var name = id.replace(/^id_/, "");
    document.querySelectorAll("select.cf-autocomplete").forEach(function (sel) {
      if (sel === changed) {
        return;
      }
      var parents = (sel.getAttribute("data-combo-parents") || "").split(",");
      var watches = parents.some(function (p) {
        return p.trim() === name;
      });
      if (!watches) {
        return;
      }
      var current = sel.options[sel.selectedIndex];
      if (current && current.value && !optionMatchesParents(current, parentValues(sel))) {
        sel.value = "";
        sel.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
  }

  ready(function () {
    document.querySelectorAll("select.cf-autocomplete").forEach(enhance);
    document.querySelectorAll("select.cf-autocomplete").forEach(function (sel) {
      sel.addEventListener("change", function () {
        syncChildren(sel);
      });
    });
  });
})();
