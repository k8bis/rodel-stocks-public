(function () {
  window.addEventListener("pageshow", async function () {
    const ok = await window.StocksCore.sessionCheck();
    if (ok) {
      window.StocksActions.bindStaticEvents();
      await window.StocksActions.loadAll();
      window.StocksActions.setActiveTab("categories");
    }
  });
})();