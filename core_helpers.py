from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

import mysql.connector
from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse

from core_config import (
    APP_BASE_PATH,
    APP_MENU_URL,
    LOGOUT_URL,
    LOGIN_FALLBACK_URL,
    SESSION_CHECK_URL,
    QTY_PRECISION,
)
from core_control_plane import get_context_info, get_session_context


def _normalize_client_name(raw_value):
    value = str(raw_value or "").strip()

    if not value:
        return ""

    upper_value = value.upper()

    if upper_value in {"CLIENT_NAME", "__CLIENT_NAME__"}:
        return ""

    if "CLIENT_NAME" in upper_value:
        return ""

    return value


def render_page(
    request: Request,
    user: str,
    app_id: int,
    client_id: int,
    authorization: str | None = None,
):
    template_path = Path("templates/stocks_template.html")
    html = template_path.read_text(encoding="utf-8")

    context = get_session_context(
        request=request,
        app_id=app_id,
        client_id=client_id,
        authorization=authorization,
    )

    if not context:
        context = get_context_info(
            request=request,
            app_id=app_id,
            client_id=client_id,
            authorization=authorization,
        )

    if not context:
        context = {}

    raw_client_name = context.get("client_name")
    client_name = _normalize_client_name(raw_client_name)

    role = str(context.get("role") or "member").strip().lower()
    is_system_admin = bool(context.get("is_system_admin"))
    is_app_client_admin = bool(context.get("is_app_client_admin"))
    is_member = bool(context.get("is_member")) if "is_member" in context else (role == "member")

    print(
        "[render_page] session-context => "
        f"app_id={app_id}, client_id={client_id}, "
        f"role={role}, "
        f"is_system_admin={is_system_admin}, "
        f"is_app_client_admin={is_app_client_admin}, "
        f"is_member={is_member}, "
        f"raw_client_name={repr(raw_client_name)}, "
        f"normalized_client_name={repr(client_name)}"
    )

    html = html.replace("__USER__", user)
    html = html.replace("__APP_ID__", str(app_id))
    html = html.replace("__CLIENT_ID__", str(client_id))
    html = html.replace("__CLIENT_NAME__", client_name)
    html = html.replace("__ROLE__", role)
    html = html.replace("__IS_SYSTEM_ADMIN__", "true" if is_system_admin else "false")
    html = html.replace("__IS_APP_CLIENT_ADMIN__", "true" if is_app_client_admin else "false")
    html = html.replace("__IS_MEMBER__", "true" if is_member else "false")
    html = html.replace("__APP_BASE_PATH__", APP_BASE_PATH)
    html = html.replace("__APP_MENU_URL__", APP_MENU_URL)
    html = html.replace("__LOGOUT_URL__", LOGOUT_URL)
    html = html.replace("__LOGIN_FALLBACK_URL__", LOGIN_FALLBACK_URL)
    html = html.replace("__SESSION_CHECK_URL__", SESSION_CHECK_URL)
    html = html.replace("__LOGOUT_REDIRECT_URL__", LOGIN_FALLBACK_URL)

    response = HTMLResponse(html)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def ok(data=None, message="OK", status_code=200):
    payload = {"ok": True, "message": message}
    if data is not None:
        payload.update(data)
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


def fail(message, status_code=400):
    return JSONResponse(status_code=status_code, content={"ok": False, "message": message})


def q3(value):
    try:
        return Decimal(str(value or 0)).quantize(QTY_PRECISION, rounding=ROUND_HALF_UP)
    except Exception:
        raise HTTPException(status_code=400, detail="Cantidad inválida")


def normalize_text(value, max_len=None):
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    if max_len:
        value = value[:max_len]
    return value


def normalize_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    return s in ("1", "true", "yes", "si", "sí", "on")


def parse_request_payload(payload: dict | None):
    payload = payload or {}
    return payload


def get_category_by_id(cur, client_id: int, category_id: int):
    cur.execute(
        """
        SELECT id, client_id, name, description, is_active, created_at, updated_at
        FROM stock_categories
        WHERE id = %s AND client_id = %s
        """,
        (category_id, client_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [c[0] for c in cur.description]
    return {cols[i]: _decimal_to_float(row[i]) for i in range(len(cols))}


def get_item_by_id(cur, client_id: int, item_id: int):
    cur.execute(
        """
        SELECT
          si.id,
          si.client_id,
          si.category_id,
          si.name,
          si.description,
          si.item_type,
          si.brand,
          si.model,
          si.color,
          si.sku,
          si.barcode,
          si.track_inventory,
          si.is_sellable,
          si.is_purchasable,
          si.unit_of_measure,
          si.min_stock,
          si.is_active,
          sc.name AS category_name
        FROM stock_items si
        LEFT JOIN stock_categories sc ON sc.id = si.category_id
        WHERE si.id = %s AND si.client_id = %s
        """,
        (item_id, client_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [c[0] for c in cur.description]
    return {cols[i]: _decimal_to_float(row[i]) for i in range(len(cols))}


def get_balance_by_item(cur, client_id: int, item_id: int):
    cur.execute(
        """
        SELECT id, client_id, stock_item_id, on_hand_qty, reserved_qty, updated_at
        FROM stock_balances
        WHERE client_id = %s AND stock_item_id = %s
        """,
        (client_id, item_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [c[0] for c in cur.description]
    return {cols[i]: _decimal_to_float(row[i]) for i in range(len(cols))}


def ensure_balance_row(cur, client_id: int, item_id: int):
    balance = get_balance_by_item(cur, client_id, item_id)
    if balance:
        return balance

    cur.execute(
        """
        INSERT INTO stock_balances (client_id, stock_item_id, on_hand_qty, reserved_qty)
        VALUES (%s, %s, 0.000, 0.000)
        """,
        (client_id, item_id),
    )
    return get_balance_by_item(cur, client_id, item_id)


def insert_movement(
    cur,
    client_id: int,
    item_id: int,
    movement_type: str,
    quantity: Decimal,
    created_by: str,
    notes: str | None = None,
    reference_type: str = "manual",
    reference_id: int | None = None,
    source_app: str = "rodel-stocks",
    source_app_id: int | None = None,
):
    cur.execute(
        """
        INSERT INTO stock_movements (
          client_id,
          stock_item_id,
          movement_type,
          quantity,
          reference_type,
          reference_id,
          source_app,
          source_app_id,
          created_by,
          notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            client_id,
            item_id,
            movement_type,
            quantity,
            reference_type,
            reference_id,
            source_app,
            source_app_id,
            created_by,
            notes,
        ),
    )
    return cur.lastrowid


def set_balance(cur, client_id: int, item_id: int, on_hand: Decimal, reserved: Decimal):
    ensure_balance_row(cur, client_id, item_id)
    cur.execute(
        """
        UPDATE stock_balances
        SET on_hand_qty = %s, reserved_qty = %s
        WHERE client_id = %s AND stock_item_id = %s
        """,
        (on_hand, reserved, client_id, item_id),
    )
    return get_balance_by_item(cur, client_id, item_id)


def apply_delta_balance(cur, client_id: int, item_id: int, delta_on_hand: Decimal):
    balance = ensure_balance_row(cur, client_id, item_id)
    current_on_hand = q3(balance["on_hand_qty"])
    current_reserved = q3(balance["reserved_qty"])

    new_on_hand = (current_on_hand + delta_on_hand).quantize(QTY_PRECISION, rounding=ROUND_HALF_UP)
    if new_on_hand < Decimal("0.000"):
        raise HTTPException(status_code=400, detail="La operación deja stock negativo")

    cur.execute(
        """
        UPDATE stock_balances
        SET on_hand_qty = %s, reserved_qty = %s
        WHERE client_id = %s AND stock_item_id = %s
        """,
        (new_on_hand, current_reserved, client_id, item_id),
    )
    return get_balance_by_item(cur, client_id, item_id)


def handle_mysql_integrity_error_for_item(exc):
    msg = str(exc).lower()
    if "uq_stock_items_client_sku" in msg:
        return fail("Ya existe un item con ese SKU para este cliente", 409)
    if "uq_stock_items_client_barcode" in msg:
        return fail("Ya existe un item con ese código de barras para este cliente", 409)
    return fail("No fue posible crear el item por restricción de integridad", 409)


def _decimal_to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    return value
