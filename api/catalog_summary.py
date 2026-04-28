from fastapi import APIRouter, Request, Header

from core_auth import require_auth_context
from core_db import db_connection, decimal_to_float

router = APIRouter()


@router.get("/api/catalog/summary")
def api_catalog_summary(
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
            SELECT COUNT(*)
            FROM stock_categories
            WHERE client_id = %s AND is_active = 1
            """,
            (client_id,),
        )
        categories_active = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(*)
            FROM stock_items
            WHERE client_id = %s AND is_active = 1
            """,
            (client_id,),
        )
        items_active = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(*)
            FROM stock_items
            WHERE client_id = %s AND is_active = 1 AND track_inventory = 1
            """,
            (client_id,),
        )
        tracked_items = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COALESCE(SUM(sb.on_hand_qty), 0)
            FROM stock_balances sb
            INNER JOIN stock_items si
              ON si.id = sb.stock_item_id
             AND si.client_id = sb.client_id
            WHERE sb.client_id = %s
              AND si.is_active = 1
            """,
            (client_id,),
        )
        total_on_hand = decimal_to_float(cur.fetchone()[0])

        cur.execute(
            """
            SELECT COUNT(*)
            FROM stock_items si
            LEFT JOIN stock_balances sb
              ON sb.stock_item_id = si.id
             AND sb.client_id = si.client_id
            WHERE si.client_id = %s
              AND si.is_active = 1
              AND si.track_inventory = 1
              AND COALESCE(sb.on_hand_qty, 0) <= COALESCE(si.min_stock, 0)
            """,
            (client_id,),
        )
        low_stock_count = cur.fetchone()[0]

        return {
            "ok": True,
            "categories_active": categories_active,
            "items_active": items_active,
            "tracked_items": tracked_items,
            "total_on_hand": total_on_hand,
            "low_stock_count": low_stock_count,
        }
    finally:
        cur.close()
        conn.close()