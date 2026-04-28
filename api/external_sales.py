from decimal import Decimal

from fastapi import APIRouter, Request, Header, HTTPException

from core_auth import require_auth_context
from core_db import db_connection
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


@router.post("/api/integrations/pos/sales-apply")
async def api_apply_pos_sale_inventory(
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_id: int | None = Header(alias="X-App-Id", default=None),
    x_client_id: int | None = Header(alias="X-Client-Id", default=None),
):
    """
    INV-4A:
    Endpoint dedicado para consumo real de inventario desde POS.
    Semántica oficial:
    - all or nothing
    - valida stock real
    - aplica movimientos reales si alcanza
    - ignora servicios
    """

    user, app_id, client_id = require_auth_context(request, authorization, x_app_id, x_client_id)
    payload = parse_request_payload(await request.json())

    sale_id = payload.get("sale_id")
    source = normalize_text(payload.get("source"), 30) or "pos"
    origin_app = normalize_text(payload.get("origin_app"), 50) or "rodelsoft-pos"
    notes = normalize_text(payload.get("notes"), 255)

    if isinstance(sale_id, str) and sale_id.isdigit():
        sale_id = int(sale_id)

    if not isinstance(sale_id, int) or sale_id <= 0:
        return fail("sale_id inválido", 400)

    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        return fail("items debe ser una lista con al menos un elemento", 400)

    conn = db_connection()
    cur = conn.cursor()

    try:
        normalized_items = []
        validation_results = []

        # ---------------------------------------------------------
        # FASE 1: VALIDACIÓN COMPLETA (sin aplicar nada todavía)
        # ---------------------------------------------------------
        for idx, raw_item in enumerate(raw_items, start=1):
            if not isinstance(raw_item, dict):
                return fail(f"items[{idx}] inválido", 400)

            stock_item_id = raw_item.get("stock_item_id")
            if isinstance(stock_item_id, str) and stock_item_id.isdigit():
                stock_item_id = int(stock_item_id)

            product_type = normalize_text(raw_item.get("product_type"), 20) or "physical"

            try:
                quantity = q3(raw_item.get("qty"))
            except HTTPException:
                return fail(f"items[{idx}].qty inválido", 400)

            if quantity <= Decimal("0.000"):
                return fail(f"items[{idx}].qty debe ser mayor a 0", 400)

            # Servicios: se ignoran explícitamente
            if product_type == "service":
                normalized_items.append({
                    "index": idx,
                    "kind": "service",
                    "stock_item_id": None,
                    "quantity": quantity,
                    "product_type": product_type,
                })
                validation_results.append({
                    "index": idx,
                    "applied": False,
                    "skipped": True,
                    "reason": "service",
                })
                continue

            if not isinstance(stock_item_id, int) or stock_item_id <= 0:
                return fail(f"items[{idx}].stock_item_id inválido para item físico", 400)

            item = get_item_by_id(cur, client_id, stock_item_id)
            if not item:
                return fail(f"El item físico items[{idx}] no existe en Stocks para este cliente", 404)

            if not bool(item.get("track_inventory", True)):
                return fail(f"El item items[{idx}] no tiene inventario habilitado", 400)

            delta = quantity * Decimal("-1")

            # Validación real usando helper actual: aplica temporalmente en transacción
            # pero aún no commit; si falla cualquier cosa se rollback total.
            balance_after = apply_delta_balance(cur, client_id, stock_item_id, delta)

            normalized_items.append({
                "index": idx,
                "kind": "physical",
                "stock_item_id": stock_item_id,
                "quantity": quantity,
                "product_type": product_type,
                "item": item,
                "balance_after": balance_after,
            })

            validation_results.append({
                "index": idx,
                "stock_item_id": stock_item_id,
                "applied": True,
                "skipped": False,
                "balance_after": balance_after,
            })

        # ---------------------------------------------------------
        # IMPORTANTE:
        # Ya se validó aplicando dentro de la transacción actual.
        # Si llegamos aquí, todos los físicos alcanzan.
        # Ahora registramos movimientos reales.
        # ---------------------------------------------------------

        movement_ids = []

        for entry in normalized_items:
            if entry["kind"] != "physical":
                continue

            movement_id = insert_movement(
                cur=cur,
                client_id=client_id,
                item_id=entry["stock_item_id"],
                movement_type="sale_exit",
                quantity=entry["quantity"],
                created_by=user,
                notes=notes or f"Venta POS #{sale_id}",
                reference_type="pos_sale",
                reference_id=sale_id,
                source_app=origin_app,
                source_app_id=app_id,
            )
            movement_ids.append(movement_id)

        conn.commit()

        return ok(
            {
                "applied": True,
                "success": True,
                "external_reference_id": sale_id,
                "movement_ids": movement_ids,
                "item_results": validation_results,
                "source": source,
                "origin_app": origin_app,
            },
            "Inventario aplicado correctamente desde POS",
            200,
        )

    except HTTPException as exc:
        conn.rollback()
        return fail(exc.detail, exc.status_code)
    except Exception as exc:
        conn.rollback()
        return fail(f"Error interno al aplicar inventario de venta POS: {exc}", 500)
    finally:
        cur.close()
        conn.close()