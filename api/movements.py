from decimal import Decimal

from fastapi import APIRouter, Request, Header, HTTPException, Query

from core_auth import require_auth_context
from core_db import db_connection, rows_to_dicts
from core_helpers import (
    ok,
    fail,
    parse_request_payload,
    normalize_text,
    q3,
    get_item_by_id,
    apply_delta_balance,
    insert_movement,
)

router = APIRouter()


def _parse_items(payload: dict) -> list[dict]:
    """
    Contrato oficial:
      items: [{ stock_item_id, quantity }]

    Compatibilidad temporal:
      stock_item_id + quantity  -> items[1]
    """
    raw_items = payload.get("items")

    if isinstance(raw_items, list) and raw_items:
        return raw_items

    legacy_item_id = payload.get("stock_item_id")
    legacy_qty = payload.get("quantity")

    if legacy_item_id is not None:
        return [
            {
                "stock_item_id": legacy_item_id,
                "quantity": legacy_qty,
            }
        ]

    raise HTTPException(status_code=400, detail="Debes enviar al menos un item en items[]")


@router.post("/api/movements")
async def api_create_movement(
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_id: int | None = Header(alias="X-App-Id", default=None),
    x_client_id: int | None = Header(alias="X-Client-Id", default=None),
):
    user, _, client_id = require_auth_context(request, authorization, x_app_id, x_client_id)
    payload = parse_request_payload(await request.json())

    movement_type = normalize_text(payload.get("movement_type"), 30)
    notes = normalize_text(payload.get("notes"), 255)

    allowed = {
        "purchase_entry": Decimal("1"),
        "manual_entry": Decimal("1"),
        "sale_exit": Decimal("-1"),
        "manual_exit": Decimal("-1"),
        "adjustment_plus": Decimal("1"),
        "adjustment_minus": Decimal("-1"),
        "sale_cancel_reversal": Decimal("1"),
    }

    if movement_type not in allowed:
        return fail(
            "movement_type inválido. Usa: purchase_entry, manual_entry, sale_exit, manual_exit, adjustment_plus, adjustment_minus, sale_cancel_reversal",
            400,
        )

    reference_type = normalize_text(payload.get("reference_type"), 30) or "manual"
    allowed_reference_types = {"purchase_order", "pos_sale", "manual"}
    if reference_type not in allowed_reference_types:
        return fail("reference_type inválido. Usa: purchase_order, pos_sale, manual", 400)

    reference_id = payload.get("reference_id")
    if reference_id is not None:
        if isinstance(reference_id, str) and reference_id.isdigit():
            reference_id = int(reference_id)
        if not isinstance(reference_id, int):
            return fail("reference_id inválido", 400)

    source_app = normalize_text(payload.get("source_app"), 100) or "rodel-stocks"

    source_app_id = payload.get("source_app_id")
    if source_app_id is not None:
        if isinstance(source_app_id, str) and source_app_id.isdigit():
            source_app_id = int(source_app_id)
        if not isinstance(source_app_id, int):
            return fail("source_app_id inválido", 400)

    try:
        items = _parse_items(payload)
    except HTTPException as exc:
        return fail(exc.detail, exc.status_code)

    conn = db_connection()
    cur = conn.cursor()

    try:
        movement_ids = []
        results = []

        for raw_item in items:
            item_id = raw_item.get("stock_item_id")
            if isinstance(item_id, str) and item_id.isdigit():
                item_id = int(item_id)

            if not isinstance(item_id, int):
                raise HTTPException(status_code=400, detail="stock_item_id inválido")

            try:
                quantity = q3(raw_item.get("quantity"))
            except HTTPException:
                raise HTTPException(status_code=400, detail="quantity inválida")

            if quantity <= Decimal("0.000"):
                raise HTTPException(status_code=400, detail="quantity debe ser mayor a 0")

            item = get_item_by_id(cur, client_id, item_id)
            if not item:
                raise HTTPException(status_code=404, detail=f"El item no existe para este cliente: {item_id}")

            delta = quantity * allowed[movement_type]
            balance = apply_delta_balance(cur, client_id, item_id, delta)

            movement_id = insert_movement(
                cur,
                client_id,
                item_id,
                movement_type,
                quantity,
                user,
                notes,
                reference_type=reference_type,
                reference_id=reference_id,
                source_app=source_app,
                source_app_id=source_app_id,
            )

            movement_ids.append(movement_id)
            results.append(
                {
                    "movement_id": movement_id,
                    "item": item,
                    "balance": balance,
                }
            )

        conn.commit()

        return ok(
            {
                "movement_ids": movement_ids,
                "items": results,
                "movement_type": movement_type,
                "reference_type": reference_type,
                "reference_id": reference_id,
                "source_app": source_app,
                "source_app_id": source_app_id,
            },
            "Movimiento(s) registrado(s)",
            201,
        )
    except HTTPException as exc:
        conn.rollback()
        return fail(exc.detail, exc.status_code)
    finally:
        cur.close()
        conn.close()


@router.get("/api/movements")
def api_movements(
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_id: int | None = Header(alias="X-App-Id", default=None),
    x_client_id: int | None = Header(alias="X-Client-Id", default=None),
    stock_item_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    _, _, client_id = require_auth_context(request, authorization, x_app_id, x_client_id)

    conn = db_connection()
    cur = conn.cursor()

    try:
        sql = """
            SELECT
              sm.id,
              sm.client_id,
              sm.stock_item_id,
              si.name AS item_name,
              si.sku,
              sm.movement_type,
              sm.quantity,
              sm.reference_type,
              sm.reference_id,
              sm.source_app,
              sm.source_app_id,
              sm.created_by,
              sm.notes,
              sm.created_at
            FROM stock_movements sm
            INNER JOIN stock_items si
              ON si.id = sm.stock_item_id
             AND si.client_id = sm.client_id
            WHERE sm.client_id = %s
        """
        params = [client_id]

        if stock_item_id is not None:
            sql += " AND sm.stock_item_id = %s "
            params.append(stock_item_id)

        sql += " ORDER BY sm.created_at DESC, sm.id DESC LIMIT %s "
        params.append(limit)

        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        return {"ok": True, "items": rows_to_dicts(cur, rows)}
    finally:
        cur.close()
        conn.close()