(function () {
  const C = () => window.StocksCore;

  function showModal(id) {
    C().qs(id)?.classList.remove("hidden");
    document.body.classList.add("rs-modal-open");
  }

  function hideModal(id) {
    C().qs(id)?.classList.add("hidden");
    if ([...document.querySelectorAll(".rs-modal-backdrop")].every((x) => x.classList.contains("hidden"))) {
      document.body.classList.remove("rs-modal-open");
    }
  }

  function closeAllModals() {
    ["categoryModal", "itemModal", "balanceModal", "movementModal"].forEach(hideModal);
  }

  function resetCategoryForm() {
    const form = C().qs("categoryForm");
    C().qs("catEditId").value = "";
    form.reset();
    C().qs("catIsActive").checked = true;
    C().qs("btnSaveCategory").textContent = "Guardar categoría";
    C().qs("categoryModalTitle").textContent = "Nueva categoría";
  }

  function openCategoryCreate() {
    resetCategoryForm();
    showModal("categoryModal");
  }

  function openCategoryEdit(item) {
    C().qs("catEditId").value = item.id;
    C().qs("catName").value = item.name || "";
    C().qs("catDescription").value = item.description || "";
    C().qs("catIsActive").checked = !!item.is_active;
    C().qs("btnSaveCategory").textContent = "Actualizar categoría";
    C().qs("categoryModalTitle").textContent = "Editar categoría";
    showModal("categoryModal");
  }

  function resetItemForm() {
    const form = C().qs("itemForm");
    C().qs("itemEditId").value = "";
    form.reset();
    C().qs("itemType").value = "physical";
    C().qs("itemUnit").value = "piece";
    C().qs("itemMinStock").value = "0";
    C().qs("itemTrackInventory").checked = true;
    C().qs("itemSellable").checked = true;
    C().qs("itemPurchasable").checked = true;
    C().qs("itemIsActive").checked = true;
    C().qs("btnSaveItem").textContent = "Guardar item";
    C().qs("itemModalTitle").textContent = "Nuevo item";
  }

  function openItemCreate() {
    resetItemForm();
    showModal("itemModal");
  }

  function openItemEdit(item) {
    C().qs("itemEditId").value = item.id;
    C().qs("itemName").value = item.name || "";
    C().qs("itemType").value = item.item_type || "physical";
    C().qs("itemCategory").value = item.category_id ? String(item.category_id) : "";
    C().qs("itemSku").value = item.sku || "";
    C().qs("itemBarcode").value = item.barcode || "";
    C().qs("itemBrand").value = item.brand || "";
    C().qs("itemModel").value = item.model || "";
    C().qs("itemColor").value = item.color || "";
    C().qs("itemUnit").value = item.unit_of_measure || "piece";
    C().qs("itemMinStock").value = String(item.min_stock ?? 0);
    C().qs("itemDescription").value = item.description || "";
    C().qs("itemTrackInventory").checked = !!item.track_inventory;
    C().qs("itemSellable").checked = !!item.is_sellable;
    C().qs("itemPurchasable").checked = !!item.is_purchasable;
    C().qs("itemIsActive").checked = !!item.is_active;
    C().qs("btnSaveItem").textContent = "Actualizar item";
    C().qs("itemModalTitle").textContent = "Editar item";
    showModal("itemModal");
  }

  function resetBalanceForm() {
    const form = C().qs("balanceForm");
    form.reset();
    C().qs("balanceOnHand").value = "0";
    C().qs("balanceReserved").value = "0";
    C().qs("balanceNotes").value = "";
  }

  function openBalanceModal() {
    resetBalanceForm();
    showModal("balanceModal");
  }

  function resetMovementForm() {
    const form = C().qs("movementForm");
    form.reset();
    C().qs("movementType").value = "manual_entry";
    C().qs("movementQty").value = "1";
    C().qs("movementNotes").value = "";
  }

  function openMovementModal() {
    resetMovementForm();
    showModal("movementModal");
  }

  function bindModalEvents() {
    [
      ["btnOpenCategoryModal", openCategoryCreate],
      ["btnOpenItemModal", openItemCreate],
      ["btnOpenBalanceModal", openBalanceModal],
      ["btnOpenMovementModal", openMovementModal],
      ["btnCloseCategoryModal", () => hideModal("categoryModal")],
      ["btnCancelCategoryEdit", () => hideModal("categoryModal")],
      ["btnCloseItemModal", () => hideModal("itemModal")],
      ["btnCancelItemEdit", () => hideModal("itemModal")],
      ["btnCloseBalanceModal", () => hideModal("balanceModal")],
      ["btnCancelBalance", () => hideModal("balanceModal")],
      ["btnCloseMovementModal", () => hideModal("movementModal")],
      ["btnCancelMovement", () => hideModal("movementModal")],
    ].forEach(([id, handler]) => {
      const el = C().qs(id);
      if (el) el.addEventListener("click", handler);
    });

    document.querySelectorAll(".rs-modal-backdrop").forEach((backdrop) => {
      backdrop.addEventListener("click", function (e) {
        if (e.target === backdrop) {
          backdrop.classList.add("hidden");
          if ([...document.querySelectorAll(".rs-modal-backdrop")].every((x) => x.classList.contains("hidden"))) {
            document.body.classList.remove("rs-modal-open");
          }
        }
      });
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        closeAllModals();
      }
    });
  }

  window.StocksModals = {
    showModal,
    hideModal,
    closeAllModals,
    resetCategoryForm,
    openCategoryCreate,
    openCategoryEdit,
    resetItemForm,
    openItemCreate,
    openItemEdit,
    resetBalanceForm,
    openBalanceModal,
    resetMovementForm,
    openMovementModal,
    bindModalEvents,
  };
})();