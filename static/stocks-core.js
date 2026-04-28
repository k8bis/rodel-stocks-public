(function () {
  const path = window.location.pathname;

  let APP_BASE = "";

  if (path.startsWith("/ext/")) {
    const parts = path.split("/");
    if (parts.length >= 3) {
      APP_BASE = `/ext/${parts[2]}`;
    }
  } else if (path.startsWith("/rodel-stocks")) {
    APP_BASE = "/rodel-stocks";
  }

  const NAV = window.RODELSOFT_NAV || {};
  const CFG = window.STOCKS_CONFIG || {};

  const APP_MENU_URL = NAV.APP_MENU_URL || CFG.APP_MENU_URL || "/";

  const LOGOUT_URL = NAV.LOGOUT_URL || CFG.LOGOUT_URL || `${APP_BASE}/logout`;


  const LOGIN_FALLBACK_URL =
    NAV.LOGIN_FALLBACK_URL ||
    CFG.LOGIN_FALLBACK_URL ||
    CFG.LOGOUT_REDIRECT_URL ||
    "/";

  const state = {
    categoriesCache: [],
    itemsCache: [],
    balancesCache: [],
    movementsCache: [],
    isBusy: false,
  };

  function qs(id) {
    return document.getElementById(id);
  }

  function getQueryString() {
    return window.location.search || "";
  }

  function goLogin() {
    window.location.replace(LOGIN_FALLBACK_URL);
  }

  async function sessionCheck() {
    try {
      const qsText = getQueryString();
      const res = await fetch(`${APP_BASE}/session-check${qsText}`, {
        credentials: "include",
        redirect: "manual",
      });

      if (res.type === "opaqueredirect" || (res.status >= 300 && res.status < 400)) {
        goLogin();
        return false;
      }

      if (!res.ok) {
        goLogin();
        return false;
      }

      return true;
    } catch {
      goLogin();
      return false;
    }
  }

  async function fetchJson(url, options = {}) {
    const res = await fetch(url, {
      credentials: "include",
      redirect: "manual",
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    if (res.type === "opaqueredirect" || (res.status >= 300 && res.status < 400)) {
      goLogin();
      throw new Error("Sesión inválida");
    }

    if (res.status === 401) {
      goLogin();
      throw new Error("No autorizado");
    }

    const text = await res.text();
    let data = null;

    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = null;
    }

    if (!res.ok) {
      const msg = (data && (data.message || data.detail)) || text || `HTTP ${res.status}`;
      throw new Error(msg);
    }

    return data;
  }

  function setBusy(value) {
    state.isBusy = !!value;

    [
      qs("btnSaveCategory"),
      qs("btnSaveItem"),
      qs("btnSaveBalance"),
      qs("btnSaveMovement"),
      qs("btnCancelCategoryEdit"),
      qs("btnCancelItemEdit"),
      qs("btnCancelBalance"),
      qs("btnCancelMovement"),
    ].forEach((btn) => {
      if (btn) btn.disabled = state.isBusy;
    });
  }

  function setStatus(text, isError = false) {
    const statusEl = qs("status");
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.toggle("error", !!isError);
  }

  function safe(v) {
    return v === null || v === undefined || v === "" ? "-" : String(v);
  }

  function fmtQty(v) {
    const n = Number(v || 0);
    return n.toLocaleString("es-MX", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 3,
    });
  }

  function esc(v) {
    return String(v ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function closeUserMenu() {
    qs("userDropdown")?.classList.remove("show");
  }

  window.StocksCore = {
    APP_BASE,
    APP_MENU_URL,
    LOGOUT_URL,
    LOGIN_FALLBACK_URL,
    state,
    qs,
    getQueryString,
    goLogin,
    sessionCheck,
    fetchJson,
    setBusy,
    setStatus,
    safe,
    fmtQty,
    esc,
    closeUserMenu,
  };
})();
