(function () {
  function findOccurrenceGroup() {
    return (
      document.getElementById("eventoccurrence_set-group") ||
      document.querySelector('[id$="occurrence_set-group"]') ||
      document.querySelector('[data-inline-formset][id*="occurrence"]') ||
      document.querySelector('.js-inline-admin-formset[id*="occurrence"]')
    );
  }

  function ensureHint(group) {
    if (!group || group.dataset.recurrenceHintMounted === "1") {
      return;
    }

    var hint = document.createElement("p");
    hint.className = "help occurrence-recurrence-hint";
    hint.textContent =
      "Enable 'Is recurring' to edit event occurrences.";
    group.parentNode.insertBefore(hint, group);

    group.dataset.recurrenceHintMounted = "1";
  }

  function setGroupEnabled(group, enabled) {
    if (!group) {
      return;
    }

    ensureHint(group);

    var hint = group.parentNode.querySelector(".occurrence-recurrence-hint");
    if (hint) {
      hint.style.display = enabled ? "none" : "block";
    }

    group.style.opacity = enabled ? "1" : "0.45";
    group.style.pointerEvents = enabled ? "auto" : "none";
    group.setAttribute("aria-disabled", enabled ? "false" : "true");

    var addButton = group.querySelector(".add-row a, .addlink");
    if (addButton) {
      addButton.tabIndex = enabled ? 0 : -1;
    }
  }

  function initRecurrenceToggle() {
    var recurringInput = document.getElementById("id_is_recurring");
    var patternInput = document.getElementById("id_recurrence_pattern");
    var weekdayInput = document.getElementById("id_recurrence_weekday");
    var group = findOccurrenceGroup();

    if (!recurringInput && !patternInput && !weekdayInput && !group) {
      return;
    }

    function findWeekdayRow() {
      if (!weekdayInput) {
        return null;
      }

      return (
        weekdayInput.closest(".form-row") ||
        weekdayInput.closest("[class*='field-recurrence_weekday']") ||
        weekdayInput.parentElement
      );
    }

    function setWeekdayVisibility(isVisible) {
      var weekdayRow = findWeekdayRow();
      if (!weekdayInput || !weekdayRow) {
        return;
      }

      weekdayRow.style.display = isVisible ? "" : "none";
      weekdayInput.disabled = !isVisible;
      if (!isVisible) {
        weekdayInput.value = "";
      }
    }

    function apply() {
      var recurringEnabled = !!(recurringInput && recurringInput.checked);
      var patternValue = (patternInput && patternInput.value) || "";
      var needsWeekday =
        recurringEnabled &&
        (patternValue === "weekly" || patternValue === "biweekly");

      if (group) {
        setGroupEnabled(group, recurringEnabled);
      }
      setWeekdayVisibility(needsWeekday);
    }

    apply();
    if (recurringInput) {
      recurringInput.addEventListener("change", apply);
    }
    if (patternInput) {
      patternInput.addEventListener("change", apply);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initRecurrenceToggle);
  } else {
    initRecurrenceToggle();
  }
})();
