from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core_config import APP_BASE_PATH
from core_db import wait_for_db
from api.catalog_summary import router as catalog_summary_router
from api.categories import router as categories_router
from api.items import router as items_router
from api.balances import router as balances_router
from api.movements import router as movements_router
from api.external_sales import router as external_sales_router
from core_auth import router as auth_router

# =========================================================
# Root app (para health del Portal)
# =========================================================
app = FastAPI(title="Rodel-Stocks Root")

# =========================================================
# Subapp real de Stocks (vive bajo APP_BASE_PATH)
# =========================================================
stocks_app = FastAPI(title="Rodel-Stocks")

# ---------------------------------------------------------
# Static files de la subapp
# Cuando la app está montada en /ext/stocks, este /static
# queda disponible como /ext/stocks/static automáticamente.
# ---------------------------------------------------------
stocks_app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def startup():
    print("[startup] Rodel-Stocks iniciado")
    print(f"[startup] APP_BASE_PATH={APP_BASE_PATH}")
    from core_config import STOCKS_MYSQL_HOST, STOCKS_MYSQL_PORT, STOCKS_MYSQL_DATABASE
    print(f"[startup] STOCKS_MYSQL_HOST={STOCKS_MYSQL_HOST}")
    print(f"[startup] STOCKS_MYSQL_PORT={STOCKS_MYSQL_PORT}")
    print(f"[startup] STOCKS_MYSQL_DATABASE={STOCKS_MYSQL_DATABASE}")
    wait_for_db()


# =========================================================
# Health raíz para que Portal siga validando con /health
# =========================================================
@app.get("/health")
def root_health():
    return {"status": "ok", "service": "rodel-stocks", "db": "ok"}


# =========================================================
# Rutas reales de Stocks (todas bajo /ext/stocks)
# =========================================================
stocks_app.include_router(auth_router)
stocks_app.include_router(catalog_summary_router)
stocks_app.include_router(categories_router)
stocks_app.include_router(items_router)
stocks_app.include_router(balances_router)
stocks_app.include_router(movements_router)
stocks_app.include_router(external_sales_router)


# =========================================================
# Montaje bajo APP_BASE_PATH
# =========================================================
if APP_BASE_PATH and APP_BASE_PATH != "/":
    app.mount(APP_BASE_PATH, stocks_app)
else:
    # fallback solo si APP_BASE_PATH viene vacío o "/"
    app.mount("/", stocks_app)
