from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Request, Header, HTTPException

from core_auth import require_auth_context
from core_db import db_connection, rows_to_dicts
from core_config import QTY_PRECISION
from core_helpers import (
    ok,
    fail,
    parse_request_payload,
    q3,
    normalize_text,
    get_item_by_id,
    ensure_balance_row,
    set_balance,
    insert_movement,
)

router = APIRouter()


@router.get("/api/balances")
def api_balances(
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
              sb.id,
              sb.client_id,
              sb.stock_item_id,
              si.name AS item_name,
              si.sku,
              sb.on_hand_qty,
              sb.reserved_qty,
              sb.updated_at
            FROM stock_balances sb
            INNER JOIN stock_items si
              ON si.id = sb.stock_item_id
             AND si.client_id = sb.client_id
            WHERE sb.client_id = %s
            ORDER BY si.name ASC
            """,
            (client_id,),
        )
        rows = cur.fetchall()
        return {"ok": True, "items": rows_to_dicts(cur, rows)}
    finally:
        cur.close()
        conn.close()


@router.post("/api/balances/upsert")
async def api_upsert_balance(
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_id: int | None = Header(alias="X-App-Id", default=None),
    x_client_id: int | None = Header(alias="X-Client-Id", default=None),
):
    user, _, client_id = require_auth_context(request, authorization, x_app_id, x_client_id)
    payload = parse_request_payload(await request.json())

    item_id = payload.get("stock_item_id")
    if isinstance(item_id, str) and item_id.isdigit():
        item_id = int(item_id)

    if not isinstance(item_id, int):
        return fail("stock_item_id inválido", 400)

    try:
        on_hand_qty = q3(payload.get("on_hand_qty", 0))
        reserved_qty = q3(payload.get("reserved_qty", 0))
    except HTTPException:
        return fail("Cantidad inválida", 400)

    if on_hand_qty < Decimal("0.000") or reserved_qty < Decimal("0.000"):
        return fail("Las cantidades no pueden ser negativas", 400)

    notes = normalize_text(payload.get("notes"), 255)

    conn = db_connection()
    cur = conn.cursor()

    try:
        item = get_item_by_id(cur, client_id, item_id)
        if not item:
            return fail("El item no existe para este cliente", 404)

        balance_before = ensure_balance_row(cur, client_id, item_id)
        prev_on_hand = q3(balance_before["on_hand_qty"])

        balance = set_balance(cur, client_id, item_id, on_hand_qty, reserved_qty)

        diff = (on_hand_qty - prev_on_hand).quantize(QTY_PRECISION, rounding=ROUND_HALF_UP)
        if diff > Decimal("0.000"):
            insert_movement(
                cur,
                client_id,
                item_id,
                "adjustment_plus",
                diff,
                user,
                notes or "Ajuste manual de balance (incremento)",
            )
        elif diff < Decimal("0.000"):
            insert_movement(
                cur,
                client_id,
                item_id,
                "adjustment_minus",
                abs(diff),
                user,
                notes or "Ajuste manual de balance (decremento)",
            )

        conn.commit()

        return ok(
            {
                "item": item,
                "balance": balance,
                "difference_on_hand": float(diff),
            },
            "Balance actualizado",
            200,
        )
    except HTTPException as exc:
        conn.rollback()
        return fail(exc.detail, exc.status_code)
    finally:
        cur.close()
        conn.close()