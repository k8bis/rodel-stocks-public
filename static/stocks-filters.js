(function () {
  const C = () => window.StocksCore;

  function containsText(value, search) {
    if (!search) return true;
    return String(value || "").toLowerCase().includes(search);
  }

  function getCategorySearch() {
    return (C().qs("filterCategoriesText")?.value || "").trim().toLowerCase();
  }

  function getItemsSearch() {
    return (C().qs("filterItemsText")?.value || "").trim().toLowerCase();
  }

  function getItemsCategory() {
    return C().qs("filterItemsCategory")?.value || "";
  }

  function getItemsActive() {
    return C().qs("filterItemsActive")?.value || "";
  }

  function getItemsTracked() {
    return C().qs("filterItemsTracked")?.value || "";
  }

  function getItemsLow() {
    return C().qs("filterItemsLow")?.value || "";
  }

  function getBalancesSearch() {
    return (C().qs("filterBalancesText")?.value || "").trim().toLowerCase();
  }

  function getMovementsSearch() {
    return (C().qs("filterMovementsText")?.value || "").trim().toLowerCase();
  }

  function getMovementsType() {
    return C().qs("filterMovementsType")?.value || "";
  }

  function getFilteredCategories(items) {
    const search = getCategorySearch();
    return (items || []).filter((item) => {
      return (
        containsText(item.name, search) ||
        containsText(item.description, search)
      );
    });
  }

  function getFilteredItems(items) {
    const search = getItemsSearch();
    const category = getItemsCategory();
    const active = getItemsActive();
    const tracked = getItemsTracked();
    const low = getItemsLow();

    return (items || []).filter((item) => {
      const matchesText =
        containsText(item.name, search) ||
        containsText(item.sku, search) ||
        containsText(item.brand, search) ||
        containsText(item.model, search) ||
        containsText(item.category_name, search);

      const matchesCategory =
        !category || String(item.category_id || "") === String(category);

      const matchesActive =
        active === "" || String(Number(!!item.is_active)) === active;

      const matchesTracked =
        tracked === "" || String(Number(!!item.track_inventory)) === tracked;

      const isLow = Number(item.on_hand_qty || 0) <= Number(item.min_stock || 0);
      const matchesLow =
        low === "" || String(Number(isLow)) === low;

      return matchesText && matchesCategory && matchesActive && matchesTracked && matchesLow;
    });
  }

  function getFilteredBalances(items) {
    const search = getBalancesSearch();

    return (items || []).filter((item) => {
      return (
        containsText(item.item_name, search) ||
        containsText(item.sku, search)
      );
    });
  }

  function getFilteredMovements(items) {
    const search = getMovementsSearch();
    const type = getMovementsType();

    return (items || []).filter((item) => {
      const matchesText =
        containsText(item.item_name, search) ||
        containsText(item.sku, search) ||
        containsText(item.notes, search) ||
        containsText(item.created_by, search);

      const matchesType = !type || String(item.movement_type || "") === type;

      return matchesText && matchesType;
    });
  }

  function resetItemQuickFilters() {
    const active = C().qs("filterItemsActive");
    const tracked = C().qs("filterItemsTracked");
    const low = C().qs("filterItemsLow");

    if (active) active.value = "";
    if (tracked) tracked.value = "";
    if (low) low.value = "";
  }

  function bindFilterEvents() {
    [
      "filterCategoriesText",
      "filterItemsText",
      "filterItemsCategory",
      "filterItemsActive",
      "filterItemsTracked",
      "filterItemsLow",
      "filterBalancesText",
      "filterMovementsText",
      "filterMovementsType",
    ].forEach((id) => {
      const el = C().qs(id);
      if (!el) return;
      el.addEventListener("input", window.StocksRender.renderAll);
      el.addEventListener("change", window.StocksRender.renderAll);
    });
  }

  window.StocksFilters = {
    getFilteredCategories,
    getFilteredItems,
    getFilteredBalances,
    getFilteredMovements,
    resetItemQuickFilters,
    bindFilterEvents,
  };
})();