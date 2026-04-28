import mysql.connector
from fastapi import APIRouter, Request, Header, HTTPException

from core_auth import require_auth_context
from core_db import db_connection, rows_to_dicts
from core_helpers import (
    ok,
    fail,
    parse_request_payload,
    normalize_text,
    normalize_bool,
    q3,
    get_category_by_id,
    get_item_by_id,
    ensure_balance_row,
    handle_mysql_integrity_error_for_item,
)

router = APIRouter()


@router.get("/api/items")
def api_items(
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_id: int | None = Header(alias="X-App-Id", default=None),
    x_client_id: int | None = Header(alias="X-Client-Id", default=None),
):
    _, _, client_id = require_auth_context(request, authorization, x_app_id, x_client_id)

    conn = db_connection()
    cur = conn.cursor()

    try:
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
              sc.name AS category_name,
              COALESCE(sb.on_hand_qty, 0) AS on_hand_qty,
              COALESCE(sb.reserved_qty, 0) AS reserved_qty
            FROM stock_items si
            LEFT JOIN stock_categories sc
              ON sc.id = si.category_id
            LEFT JOIN stock_balances sb
              ON sb.stock_item_id = si.id
             AND sb.client_id = si.client_id
            WHERE si.client_id = %s
            ORDER BY si.is_active DESC, si.name ASC
            """,
            (client_id,),
        )
        rows = cur.fetchall()
        return {"ok": True, "items": rows_to_dicts(cur, rows)}
    finally:
        cur.close()
        conn.close()


@router.post("/api/items")
async def api_create_item(
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_id: int | None = Header(alias="X-App-Id", default=None),
    x_client_id: int | None = Header(alias="X-Client-Id", default=None),
):
    user, _, client_id = require_auth_context(request, authorization, x_app_id, x_client_id)
    payload = parse_request_payload(await request.json())

    category_id = payload.get("category_id")
    if category_id in ("", None):
        category_id = None
    elif isinstance(category_id, str) and category_id.isdigit():
        category_id = int(category_id)
    elif not isinstance(category_id, int):
        return fail("category_id inválido", 400)

    name = normalize_text(payload.get("name"), 200)
    description = normalize_text(payload.get("description"))
    item_type = normalize_text(payload.get("item_type"), 20) or "physical"
    brand = normalize_text(payload.get("brand"), 100)
    model = normalize_text(payload.get("model"), 100)
    color = normalize_text(payload.get("color"), 50)
    sku = normalize_text(payload.get("sku"), 50)
    barcode = normalize_text(payload.get("barcode"), 50)
    track_inventory = 1 if normalize_bool(payload.get("track_inventory"), True) else 0
    is_sellable = 1 if normalize_bool(payload.get("is_sellable"), True) else 0
    is_purchasable = 1 if normalize_bool(payload.get("is_purchasable"), True) else 0
    unit_of_measure = normalize_text(payload.get("unit_of_measure"), 30) or "piece"
    is_active = 1 if normalize_bool(payload.get("is_active"), True) else 0

    try:
        min_stock = q3(payload.get("min_stock", 0))
    except HTTPException:
        return fail("min_stock inválido", 400)

    if not name:
        return fail("El nombre del item es obligatorio", 400)

    if item_type not in ("physical", "service"):
        return fail("item_type inválido. Usa 'physical' o 'service'", 400)

    conn = db_connection()
    cur = conn.cursor()

    try:
        if category_id is not None:
            category = get_category_by_id(cur, client_id, category_id)
            if not category:
                return fail("La categoría no existe para este cliente", 404)

        cur.execute(
            """
            INSERT INTO stock_items (
              client_id,
              category_id,
              name,
              description,
              item_type,
              brand,
              model,
              color,
              sku,
              barcode,
              track_inventory,
              is_sellable,
              is_purchasable,
              unit_of_measure,
              min_stock,
              is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                client_id,
                category_id,
                name,
                description,
                item_type,
                brand,
                model,
                color,
                sku,
                barcode,
                track_inventory,
                is_sellable,
                is_purchasable,
                unit_of_measure,
                min_stock,
                is_active,
            ),
        )
        item_id = cur.lastrowid

        if track_inventory:
            ensure_balance_row(cur, client_id, item_id)

        conn.commit()

        item = get_item_by_id(cur, client_id, item_id)
        return ok({"item": item, "created_by": user}, "Item creado", 201)

    except mysql.connector.IntegrityError as exc:
        conn.rollback()
        return handle_mysql_integrity_error_for_item(exc)
    finally:
        cur.close()
        conn.close()


@router.put("/api/items/{item_id}")
async def api_update_item(
    item_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_id: int | None = Header(alias="X-App-Id", default=None),
    x_client_id: int | None = Header(alias="X-Client-Id", default=None),
):
    user, _, client_id = require_auth_context(request, authorization, x_app_id, x_client_id)
    payload = parse_request_payload(await request.json())

    category_id = payload.get("category_id")
    if category_id in ("", None):
        category_id = None
    elif isinstance(category_id, str) and category_id.isdigit():
        category_id = int(category_id)
    elif not isinstance(category_id, int):
        return fail("category_id inválido", 400)

    name = normalize_text(payload.get("name"), 200)
    description = normalize_text(payload.get("description"))
    item_type = normalize_text(payload.get("item_type"), 20) or "physical"
    brand = normalize_text(payload.get("brand"), 100)
    model = normalize_text(payload.get("model"), 100)
    color = normalize_text(payload.get("color"), 50)
    sku = normalize_text(payload.get("sku"), 50)
    barcode = normalize_text(payload.get("barcode"), 50)
    track_inventory = 1 if normalize_bool(payload.get("track_inventory"), True) else 0
    is_sellable = 1 if normalize_bool(payload.get("is_sellable"), True) else 0
    is_purchasable = 1 if normalize_bool(payload.get("is_purchasable"), True) else 0
    unit_of_measure = normalize_text(payload.get("unit_of_measure"), 30) or "piece"
    is_active = 1 if normalize_bool(payload.get("is_active"), True) else 0

    try:
        min_stock = q3(payload.get("min_stock", 0))
    except HTTPException:
        return fail("min_stock inválido", 400)

    if not name:
        return fail("El nombre del item es obligatorio", 400)

    if item_type not in ("physical", "service"):
        return fail("item_type inválido. Usa 'physical' o 'service'", 400)

    conn = db_connection()
    cur = conn.cursor()

    try:
        current = get_item_by_id(cur, client_id, item_id)
        if not current:
            return fail("El item no existe para este cliente", 404)

        if category_id is not None:
            category = get_category_by_id(cur, client_id, category_id)
            if not category:
                return fail("La categoría no existe para este cliente", 404)

        cur.execute(
            """
            UPDATE stock_items
            SET
              category_id = %s,
              name = %s,
              description = %s,
              item_type = %s,
              brand = %s,
              model = %s,
              color = %s,
              sku = %s,
              barcode = %s,
              track_inventory = %s,
              is_sellable = %s,
              is_purchasable = %s,
              unit_of_measure = %s,
              min_stock = %s,
              is_active = %s
            WHERE id = %s
              AND client_id = %s
            """,
            (
                category_id,
                name,
                description,
                item_type,
                brand,
                model,
                color,
                sku,
                barcode,
                track_inventory,
                is_sellable,
                is_purchasable,
                unit_of_measure,
                min_stock,
                is_active,
                item_id,
                client_id,
            ),
        )

        if track_inventory:
            ensure_balance_row(cur, client_id, item_id)

        conn.commit()

        item = get_item_by_id(cur, client_id, item_id)
        return ok({"item": item, "updated_by": user}, "Item actualizado", 200)

    except mysql.connector.IntegrityError as exc:
        conn.rollback()
        return handle_mysql_integrity_error_for_item(exc)
    finally:
        cur.close()
        conn.close()