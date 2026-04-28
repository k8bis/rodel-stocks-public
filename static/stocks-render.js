(function () {
  const C = () => window.StocksCore;
  const F = () => window.StocksFilters;
  const M = () => window.StocksModals;

  function renderSummary(data) {
    C().qs("summaryCategories").textContent = C().safe(data.categories_active);
    C().qs("summaryItems").textContent = C().safe(data.items_active);
    C().qs("summaryTracked").textContent = C().safe(data.tracked_items);
    C().qs("summaryOnHand").textContent = C().fmtQty(data.total_on_hand);
    C().qs("summaryLow").textContent = C().safe(data.low_stock_count);
  }

  function buildCategoryCounts() {
    const map = new Map();

    (C().state.itemsCache || []).forEach((item) => {
      const key = item.category_id == null ? "__none__" : String(item.category_id);
      map.set(key, (map.get(key) || 0) + 1);
    });

    return map;
  }

  function renderCategories(items) {
    const list = C().qs("categoriesList");
    const empty = C().qs("categoriesEmpty");
    list.innerHTML = "";

    if (!items || items.length === 0) {
      empty.style.display = "block";
      return;
    }

    empty.style.display = "none";

    const counts = buildCategoryCounts();

    items.forEach((item) => {
      const itemCount = counts.get(String(item.id)) || 0;
      const label = `${itemCount} ${itemCount === 1 ? "item" : "items"}`;

      const div = document.createElement("div");
      div.className = "mini-card";
      div.innerHTML = `
        <div class="mini-top">
          <div class="mini-title">${C().esc(C().safe(item.name))}</div>
          <div class="mini-count">${C().esc(label)}</div>
        </div>
        <div class="mini-meta">${C().esc(C().safe(item.description))}</div>
        <div class="mini-badges">
          <span class="badge ${item.is_active ? "ok" : "off"}">
            ${item.is_active ? "Activa" : "Inactiva"}
          </span>
        </div>
        <div class="mini-actions">
          <button type="button" class="rs-btn rs-btn-secondary btn-mini-action" data-edit-category="${item.id}">
            Editar
          </button>
        </div>
      `;
      list.appendChild(div);
    });

    list.querySelectorAll("[data-edit-category]").forEach((btn) => {
      btn.addEventListener("click", function () {
        const id = String(btn.getAttribute("data-edit-category"));
        const found = C().state.categoriesCache.find((x) => String(x.id) === id);
        if (found) M().openCategoryEdit(found);
      });
    });
  }

  function renderItems(items) {
    const tbody = C().qs("itemsTbody");
    const empty = C().qs("itemsEmpty");
    tbody.innerHTML = "";

    if (!items || items.length === 0) {
      empty.style.display = "block";
      return;
    }

    empty.style.display = "none";

    items.forEach((item) => {
      const onHand = Number(item.on_hand_qty || 0);
      const minStock = Number(item.min_stock || 0);
      const low = onHand <= minStock;
      const brand = C().safe(item.brand);
      const model = C().safe(item.model);
      const sub = model === "-" ? brand : `${brand} · ${model}`;

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>
          <div class="td-title">${C().esc(C().safe(item.name))}</div>
          <div class="td-sub">${C().esc(sub)}</div>
        </td>
        <td>${C().esc(C().safe(item.item_type))}</td>
        <td>${C().esc(C().safe(item.category_name))}</td>
        <td>${C().esc(C().safe(item.sku))}</td>
        <td><span class="${low ? "qty-low" : "qty-ok"}">${C().fmtQty(item.on_hand_qty)}</span></td>
        <td>${C().fmtQty(item.min_stock)}</td>
        <td>${item.is_active ? "Sí" : "No"}</td>
        <td>
          <button type="button" class="rs-btn rs-btn-secondary btn-mini-action" data-edit-item="${item.id}">
            Editar
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll("[data-edit-item]").forEach((btn) => {
      btn.addEventListener("click", function () {
        const id = String(btn.getAttribute("data-edit-item"));
        const found = C().state.itemsCache.find((x) => String(x.id) === id);
        if (found) M().openItemEdit(found);
      });
    });
  }

  function renderBalances(items) {
    const tbody = C().qs("balancesTbody");
    const empty = C().qs("balancesEmpty");
    tbody.innerHTML = "";

    if (!items || items.length === 0) {
      empty.style.display = "block";
      return;
    }

    empty.style.display = "none";

    items.forEach((item) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${C().esc(C().safe(item.item_name))}</td>
        <td>${C().esc(C().safe(item.sku))}</td>
        <td>${C().fmtQty(item.on_hand_qty)}</td>
        <td>${C().fmtQty(item.reserved_qty)}</td>
        <td>${C().esc(C().safe(item.updated_at))}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderMovements(items) {
    const tbody = C().qs("movementsTbody");
    const empty = C().qs("movementsEmpty");
    tbody.innerHTML = "";

    if (!items || items.length === 0) {
      empty.style.display = "block";
      return;
    }

    empty.style.display = "none";

    items.forEach((item) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${C().esc(C().safe(item.created_at))}</td>
        <td>${C().esc(C().safe(item.item_name))}</td>
        <td>${C().esc(C().safe(item.sku))}</td>
        <td>${C().esc(C().safe(item.movement_type))}</td>
        <td>${C().fmtQty(item.quantity)}</td>
        <td>${C().esc(C().safe(item.created_by))}</td>
        <td>${C().esc(C().safe(item.notes))}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function fillItemSelect(selectEl, items) {
    if (!selectEl) return;
    const current = selectEl.value;
    selectEl.innerHTML = "";

    if (!items || items.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Sin items";
      selectEl.appendChild(opt);
      return;
    }

    items.forEach((item) => {
      const opt = document.createElement("option");
      opt.value = item.id;
      opt.textContent = `${item.name}${item.sku ? ` (${item.sku})` : ""}`;
      selectEl.appendChild(opt);
    });

    if ([...selectEl.options].some((o) => o.value === current)) {
      selectEl.value = current;
    }
  }

  function fillCategorySelects(categories) {
    const itemCategory = C().qs("itemCategory");
    const filterItemsCategory = C().qs("filterItemsCategory");

    const currentItem = itemCategory?.value || "";
    if (itemCategory) {
      itemCategory.innerHTML = `<option value="">Sin categoría</option>`;

      (categories || []).forEach((cat) => {
        const opt = document.createElement("option");
        opt.value = cat.id;
        opt.textContent = cat.name;
        itemCategory.appendChild(opt);
      });

      if ([...itemCategory.options].some((o) => o.value === currentItem)) {
        itemCategory.value = currentItem;
      }
    }

    const currentFilter = filterItemsCategory?.value || "";
    if (filterItemsCategory) {
      filterItemsCategory.innerHTML = `<option value="">Todas</option>`;

      (categories || []).forEach((cat) => {
        const opt = document.createElement("option");
        opt.value = String(cat.id);
        opt.textContent = cat.name;
        filterItemsCategory.appendChild(opt);
      });

      if ([...filterItemsCategory.options].some((o) => o.value === currentFilter)) {
        filterItemsCategory.value = currentFilter;
      }
    }
  }

  function normalizeClientName(rawValue) {
    const value = String(rawValue || "").trim();

    if (!value) return "";
    if (value === "CLIENT_NAME") return "";
    if (value === "__CLIENT_NAME__") return "";
    if (value.includes("CLIENT_NAME")) return "";

    return value;
  }

  function renderClientHeader() {
    const clientName = normalizeClientName(window.STOCKS_CONFIG?.CLIENT_NAME);
    const heroClientName = C().qs("heroClientName");
    const heroClientSubtitle = C().qs("heroClientSubtitle");

    if (heroClientName) {
      heroClientName.textContent = clientName;
    }

    if (heroClientSubtitle) {
      heroClientSubtitle.textContent = "";
    }
  }

  function renderAll() {
    renderClientHeader();
    renderSummary(window.StocksActions.lastSummary || {});
    renderCategories(F().getFilteredCategories(C().state.categoriesCache));
    renderItems(F().getFilteredItems(C().state.itemsCache));
    renderBalances(F().getFilteredBalances(C().state.balancesCache));
    renderMovements(F().getFilteredMovements(C().state.movementsCache));
    fillCategorySelects(C().state.categoriesCache);
    fillItemSelect(C().qs("balanceItem"), C().state.itemsCache);
    fillItemSelect(C().qs("movementItem"), C().state.itemsCache);
  }

  window.StocksRender = {
    renderSummary,
    renderCategories,
    renderItems,
    renderBalances,
    renderMovements,
    fillItemSelect,
    fillCategorySelects,
    renderClientHeader,
    renderAll,
  };
})();