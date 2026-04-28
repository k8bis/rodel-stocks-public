(function () {
  const C = () => window.StocksCore;
  const R = () => window.StocksRender;
  const F = () => window.StocksFilters;
  const M = () => window.StocksModals;

  let staticEventsBound = false;
  let lastSummary = {};
  let activeTab = "categories";

  function validateCategoryForm() {
    if (!C().qs("catName").value.trim()) {
      throw new Error("El nombre de la categoría es obligatorio.");
    }
  }

  function validateItemForm() {
    if (!C().qs("itemName").value.trim()) {
      throw new Error("El nombre del item es obligatorio.");
    }

    const minStock = Number(C().qs("itemMinStock").value || 0);
    if (Number.isNaN(minStock) || minStock < 0) {
      throw new Error("El stock mínimo debe ser 0 o mayor.");
    }

    const sku = C().qs("itemSku").value.trim();
    const itemEditId = C().qs("itemEditId").value;

    if (sku) {
      const duplicate = C().state.itemsCache.find((x) => {
        if (itemEditId && String(x.id) === String(itemEditId)) return false;
        return String(x.sku || "").trim().toLowerCase() === sku.toLowerCase();
      });

      if (duplicate) {
        throw new Error("Ya existe un item con ese SKU.");
      }
    }
  }

  function validateBalanceForm() {
    if (!C().qs("balanceItem").value) {
      throw new Error("Debes seleccionar un item.");
    }

    const onHand = Number(C().qs("balanceOnHand").value || 0);
    const reserved = Number(C().qs("balanceReserved").value || 0);

    if (Number.isNaN(onHand) || onHand < 0) {
      throw new Error("On hand debe ser 0 o mayor.");
    }

    if (Number.isNaN(reserved) || reserved < 0) {
      throw new Error("Reservado debe ser 0 o mayor.");
    }
  }

  function validateMovementForm() {
    if (!C().qs("movementItem").value) {
      throw new Error("Debes seleccionar un item.");
    }

    const qty = Number(C().qs("movementQty").value || 0);
    if (Number.isNaN(qty) || qty <= 0) {
      throw new Error("La cantidad debe ser mayor a 0.");
    }
  }

  function setActiveTab(tabName) {
    activeTab = tabName;

    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabName);
    });

    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.toggle("active", panel.getAttribute("data-panel") === tabName);
    });

    document.querySelectorAll(".summary-card-action").forEach((card) => {
      card.classList.remove("active");
    });
  }

  function applySummaryShortcut(action) {
    document.querySelectorAll(".summary-card-action").forEach((card) => {
      card.classList.toggle("active", card.getAttribute("data-summary-action") === action);
    });

    if (action === "categories") {
      setActiveTab("categories");
      document.querySelectorAll(".summary-card-action").forEach((card) => {
        card.classList.toggle("active", card.getAttribute("data-summary-action") === action);
      });
      return;
    }

    if (action === "balances") {
      setActiveTab("balances");
      document.querySelectorAll(".summary-card-action").forEach((card) => {
        card.classList.toggle("active", card.getAttribute("data-summary-action") === action);
      });
      return;
    }

    if (action === "items_active") {
      setActiveTab("items");
      F().resetItemQuickFilters();
      C().qs("filterItemsActive").value = "1";
      R().renderAll();
    } else if (action === "items_tracked") {
      setActiveTab("items");
      F().resetItemQuickFilters();
      C().qs("filterItemsTracked").value = "1";
      R().renderAll();
    } else if (action === "items_low") {
      setActiveTab("items");
      F().resetItemQuickFilters();
      C().qs("filterItemsLow").value = "1";
      R().renderAll();
    }

    document.querySelectorAll(".summary-card-action").forEach((card) => {
      card.classList.toggle("active", card.getAttribute("data-summary-action") === action);
    });
  }

  async function loadAll() {
    try {
      C().setStatus("Cargando datos de stocks_db...");
      const qs = C().getQueryString();

      const results = await Promise.allSettled([
        C().fetchJson(`${C().APP_BASE}/api/catalog/summary${qs}`),
        C().fetchJson(`${C().APP_BASE}/api/categories${qs}`),
        C().fetchJson(`${C().APP_BASE}/api/items${qs}`),
        C().fetchJson(`${C().APP_BASE}/api/balances${qs}`),
        C().fetchJson(`${C().APP_BASE}/api/movements${qs}`),
      ]);

      const [summaryRes, categoriesRes, itemsRes, balancesRes, movementsRes] = results;

      const summary = summaryRes.status === "fulfilled" ? summaryRes.value : {};
      const categories = categoriesRes.status === "fulfilled" ? categoriesRes.value : { items: [] };
      const items = itemsRes.status === "fulfilled" ? itemsRes.value : { items: [] };
      const balances = balancesRes.status === "fulfilled" ? balancesRes.value : { items: [] };
      const movements = movementsRes.status === "fulfilled" ? movementsRes.value : { items: [] };

      lastSummary = summary || {};
      C().state.categoriesCache = categories.items || [];
      C().state.itemsCache = items.items || [];
      C().state.balancesCache = balances.items || [];
      C().state.movementsCache = movements.items || [];

      R().renderAll();
      setActiveTab(activeTab);

      const failed = results.filter((x) => x.status === "rejected");
      if (failed.length > 0) {
        console.error("[stocks-actions] loadAll partial failures:", failed);
        C().setStatus("Datos cargados parcialmente. Revise consola para detalles.", true);
      } else {
        C().setStatus("Datos cargados correctamente.");
      }
    } catch (err) {
      console.error(err);
      C().setStatus(err.message || "Error cargando datos de Rodel-Stocks.", true);
    }
  }

  async function submitCategory(e) {
    e.preventDefault();
    if (C().state.isBusy) return;

    try {
      validateCategoryForm();
      C().setBusy(true);

      const editId = C().qs("catEditId").value;
      C().setStatus(editId ? "Actualizando categoría..." : "Guardando categoría...");

      const qs = C().getQueryString();

      if (!editId) {
        await C().fetchJson(`${C().APP_BASE}/api/categories${qs}`, {
          method: "POST",
          body: JSON.stringify({
            name: C().qs("catName").value.trim(),
            description: C().qs("catDescription").value.trim(),
            is_active: C().qs("catIsActive").checked,
          }),
        });
      } else {
        const found = C().state.categoriesCache.find((x) => String(x.id) === String(editId));
        if (!found) throw new Error("La categoría a editar ya no existe en pantalla.");

        await C().fetchJson(`${C().APP_BASE}/api/categories/${editId}${qs}`, {
          method: "PUT",
          body: JSON.stringify({
            name: C().qs("catName").value.trim(),
            description: C().qs("catDescription").value.trim(),
            is_active: C().qs("catIsActive").checked,
          }),
        });
      }

      M().resetCategoryForm();
      M().hideModal("categoryModal");
      await loadAll();
      setActiveTab("categories");
      C().setStatus("Categoría guardada correctamente.");
    } catch (err) {
      console.error(err);
      C().setStatus(err.message || "Error guardando categoría.", true);
    } finally {
      C().setBusy(false);
    }
  }

  async function submitItem(e) {
    e.preventDefault();
    if (C().state.isBusy) return;

    try {
      validateItemForm();
      C().setBusy(true);

      const editId = C().qs("itemEditId").value;
      C().setStatus(editId ? "Actualizando item..." : "Guardando item...");

      const qs = C().getQueryString();

      const payload = {
        name: C().qs("itemName").value.trim(),
        item_type: C().qs("itemType").value,
        category_id: C().qs("itemCategory").value || null,
        sku: C().qs("itemSku").value.trim(),
        barcode: C().qs("itemBarcode").value.trim(),
        brand: C().qs("itemBrand").value.trim(),
        model: C().qs("itemModel").value.trim(),
        color: C().qs("itemColor").value.trim(),
        unit_of_measure: C().qs("itemUnit").value.trim() || "piece",
        min_stock: C().qs("itemMinStock").value || 0,
        description: C().qs("itemDescription").value.trim(),
        track_inventory: C().qs("itemTrackInventory").checked,
        is_sellable: C().qs("itemSellable").checked,
        is_purchasable: C().qs("itemPurchasable").checked,
        is_active: C().qs("itemIsActive").checked,
      };

      if (!editId) {
        await C().fetchJson(`${C().APP_BASE}/api/items${qs}`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
      } else {
        const found = C().state.itemsCache.find((x) => String(x.id) === String(editId));
        if (!found) throw new Error("El item a editar ya no existe en pantalla.");

        await C().fetchJson(`${C().APP_BASE}/api/items/${editId}${qs}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      }

      M().resetItemForm();
      M().hideModal("itemModal");
      await loadAll();
      setActiveTab("items");
      C().setStatus("Item guardado correctamente.");
    } catch (err) {
      console.error(err);
      C().setStatus(err.message || "Error guardando item.", true);
    } finally {
      C().setBusy(false);
    }
  }

  async function submitBalance(e) {
    e.preventDefault();
    if (C().state.isBusy) return;

    try {
      validateBalanceForm();
      C().setBusy(true);
      C().setStatus("Aplicando balance...");

      const qs = C().getQueryString();

      await C().fetchJson(`${C().APP_BASE}/api/balances/upsert${qs}`, {
        method: "POST",
        body: JSON.stringify({
          stock_item_id: C().qs("balanceItem").value,
          on_hand_qty: C().qs("balanceOnHand").value || 0,
          reserved_qty: C().qs("balanceReserved").value || 0,
          notes: C().qs("balanceNotes").value.trim(),
        }),
      });

      M().resetBalanceForm();
      M().hideModal("balanceModal");
      await loadAll();
      setActiveTab("balances");
      C().setStatus("Balance actualizado correctamente.");
    } catch (err) {
      console.error(err);
      C().setStatus(err.message || "Error actualizando balance.", true);
    } finally {
      C().setBusy(false);
    }
  }

  async function submitMovement(e) {
    e.preventDefault();
    if (C().state.isBusy) return;

    try {
      validateMovementForm();
      C().setBusy(true);
      C().setStatus("Registrando movimiento...");

      const qs = C().getQueryString();

      await C().fetchJson(`${C().APP_BASE}/api/movements${qs}`, {
        method: "POST",
        body: JSON.stringify({
          movement_type: C().qs("movementType").value,
          reference_type: "manual",
          source_app: "rodel-stocks",
          items: [
            {
              stock_item_id: C().qs("movementItem").value,
              quantity: C().qs("movementQty").value || 0,
            },
          ],
          notes: C().qs("movementNotes").value.trim(),
        }),
      });

      M().resetMovementForm();
      M().hideModal("movementModal");
      await loadAll();
      setActiveTab("movements");
      C().setStatus("Movimiento registrado correctamente.");
    } catch (err) {
      console.error(err);
      C().setStatus(err.message || "Error registrando movimiento.", true);
    } finally {
      C().setBusy(false);
    }
  }

  function bindUserMenu() {
    C().qs("userMenuBtn")?.addEventListener("click", function (e) {
      e.stopPropagation();
      C().qs("userDropdown")?.classList.toggle("show");
    });

    document.addEventListener("click", function () {
      C().closeUserMenu();
    });

    C().qs("userDropdown")?.addEventListener("click", function (e) {
      e.stopPropagation();
    });

    C().qs("btnApps")?.addEventListener("click", function () {
      window.location.href = C().APP_MENU_URL;
    });

    C().qs("btnReload")?.addEventListener("click", async function () {
      if (C().state.isBusy) return;
      await loadAll();
    });

    C().qs("btnLogout")?.addEventListener("click", function () {
      C().closeUserMenu();

      try {
        window.location.replace("/logout");
      } catch {
        C().goLogin();
      }
    });
  }

  function bindTabs() {
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", function () {
        const tab = btn.getAttribute("data-tab");
        if (tab) setActiveTab(tab);
      });
    });
  }

  function bindSummaryCards() {
    document.querySelectorAll(".summary-card-action").forEach((card) => {
      card.addEventListener("click", function () {
        const action = card.getAttribute("data-summary-action");
        if (action) applySummaryShortcut(action);
      });
    });
  }

  function bindForms() {
    C().qs("categoryForm")?.addEventListener("submit", submitCategory);
    C().qs("itemForm")?.addEventListener("submit", submitItem);
    C().qs("balanceForm")?.addEventListener("submit", submitBalance);
    C().qs("movementForm")?.addEventListener("submit", submitMovement);
  }

  function bindStaticEvents() {
    if (staticEventsBound) return;

    try {
      bindUserMenu();
      bindTabs();
      bindSummaryCards();
      bindForms();

      if (F() && typeof F().bindFilterEvents === "function") {
        F().bindFilterEvents();
      }

      if (M() && typeof M().bindModalEvents === "function") {
        M().bindModalEvents();
      }

      staticEventsBound = true;
    } catch (err) {
      console.error("[stocks-actions] bindStaticEvents failed:", err);
      staticEventsBound = false;
    }
  }

  window.StocksActions = {
    get lastSummary() {
      return lastSummary;
    },
    get activeTab() {
      return activeTab;
    },
    setActiveTab,
    applySummaryShortcut,
    loadAll,
    bindStaticEvents,
  };
})();
