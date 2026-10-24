// Guided discovery interview — client-side state across categories (Phase 8).
// Answers accumulate in sessionStorage under 'wr_interview_answers'.

(function () {
  "use strict";

  var STORAGE_KEY = "wr_interview_answers";
  var section = document.querySelector(".wr-interview-category");
  if (!section) return;

  var index = parseInt(section.dataset.index, 10);
  var categoryKey = section.dataset.categoryKey;
  var isLast = section.dataset.isLast === "true";
  var categoryCount = parseInt(section.dataset.categoryCount, 10);

  var form = document.getElementById("wr-category-form");
  var usesSel = document.getElementById("wr-uses");
  var detail = document.getElementById("wr-detail-questions");
  var backupSel = document.getElementById("wr-backup");
  var backupNameLabel = document.getElementById("wr-backup-name-label");
  var docsSel = document.getElementById("wr-docs");
  var docLocationLabel = document.getElementById("wr-doc-location-label");

  function loadAll() {
    try {
      return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "[]");
    } catch (e) {
      return [];
    }
  }

  function saveAll(list) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  }

  function currentAnswersFromForm() {
    var data = { category_key: categoryKey };
    new FormData(form).forEach(function (v, k) { data[k] = v; });
    return data;
  }

  function prefill() {
    var all = loadAll();
    var existing = all.find(function (a) { return a.category_key === categoryKey; });
    if (!existing) return;
    Object.keys(existing).forEach(function (k) {
      var el = form.elements[k];
      if (el) el.value = existing[k];
    });
  }

  function storeCurrent() {
    var all = loadAll();
    var data = currentAnswersFromForm();
    var idx = all.findIndex(function (a) { return a.category_key === categoryKey; });
    if (idx >= 0) all[idx] = data; else all.push(data);
    saveAll(all);
  }

  function storeSkip() {
    // Remove any stored answer for this category so it produces no records.
    var all = loadAll().filter(function (a) { return a.category_key !== categoryKey; });
    saveAll(all);
  }

  function syncConditionals() {
    detail.hidden = usesSel.value !== "yes";
    backupNameLabel.hidden = !(usesSel.value === "yes" && backupSel.value === "yes");
    docLocationLabel.hidden = !(usesSel.value === "yes" && docsSel.value === "yes");
  }

  usesSel.addEventListener("change", syncConditionals);
  backupSel.addEventListener("change", syncConditionals);
  docsSel.addEventListener("change", syncConditionals);

  function goNext() {
    if (isLast) {
      window.location.href = "/interview/review";
    } else {
      window.location.href = "/interview/category/" + (index + 1);
    }
  }

  document.getElementById("wr-next").addEventListener("click", function () {
    storeCurrent();
    goNext();
  });

  document.getElementById("wr-skip").addEventListener("click", function () {
    storeSkip();
    goNext();
  });

  document.getElementById("wr-back").addEventListener("click", function () {
    storeCurrent();
    if (index === 0) {
      window.location.href = "/interview";
    } else {
      window.location.href = "/interview/category/" + (index - 1);
    }
  });

  prefill();
  syncConditionals();
})();
