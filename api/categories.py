import mysql.connector
from fastapi import APIRouter, Request, Header

from core_auth import require_auth_context
from core_db import db_connection, rows_to_dicts
from core_helpers import (
    ok,
    fail,
    parse_request_payload,
    normalize_text,
    normalize_bool,
    get_category_by_id,
)

router = APIRouter()


@router.get("/api/categories")
def api_categories(
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
              id,
              client_id,
              name,
              description,
              is_active,
              created_at,
              updated_at
            FROM stock_categories
            WHERE client_id = %s
            ORDER BY is_active DESC, name ASC
            """,
            (client_id,),
        )
        rows = cur.fetchall()
        return {"ok": True, "items": rows_to_dicts(cur, rows)}
    finally:
        cur.close()
        conn.close()


@router.post("/api/categories")
async def api_create_category(
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_id: int | None = Header(alias="X-App-Id", default=None),
    x_client_id: int | None = Header(alias="X-Client-Id", default=None),
):
    user, _, client_id = require_auth_context(request, authorization, x_app_id, x_client_id)
    payload = parse_request_payload(await request.json())

    name = normalize_text(payload.get("name"), 150)
    description = normalize_text(payload.get("description"))
    is_active = 1 if normalize_bool(payload.get("is_active"), True) else 0

    if not name:
        return fail("El nombre de categoría es obligatorio", 400)

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO stock_categories (client_id, name, description, is_active)
            VALUES (%s, %s, %s, %s)
            """,
            (client_id, name, description, is_active),
        )
        category_id = cur.lastrowid
        conn.commit()

        category = get_category_by_id(cur, client_id, category_id)
        return ok({"item": category, "created_by": user}, "Categoría creada", 201)

    except mysql.connector.IntegrityError:
        conn.rollback()
        return fail("Ya existe una categoría con ese nombre para este cliente", 409)
    finally:
        cur.close()
        conn.close()


@router.put("/api/categories/{category_id}")
async def api_update_category(
    category_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_id: int | None = Header(alias="X-App-Id", default=None),
    x_client_id: int | None = Header(alias="X-Client-Id", default=None),
):
    user, _, client_id = require_auth_context(request, authorization, x_app_id, x_client_id)
    payload = parse_request_payload(await request.json())

    name = normalize_text(payload.get("name"), 150)
    description = normalize_text(payload.get("description"))
    is_active = 1 if normalize_bool(payload.get("is_active"), True) else 0

    if not name:
        return fail("El nombre de categoría es obligatorio", 400)

    conn = db_connection()
    cur = conn.cursor()

    try:
        current = get_category_by_id(cur, client_id, category_id)
        if not current:
            return fail("La categoría no existe para este cliente", 404)

        cur.execute(
            """
            UPDATE stock_categories
            SET
              name = %s,
              description = %s,
              is_active = %s
            WHERE id = %s
              AND client_id = %s
            """,
            (name, description, is_active, category_id, client_id),
        )
        conn.commit()

        category = get_category_by_id(cur, client_id, category_id)
        return ok({"item": category, "updated_by": user}, "Categoría actualizada", 200)

    except mysql.connector.IntegrityError:
        conn.rollback()
        return fail("Ya existe una categoría con ese nombre para este cliente", 409)
    finally:
        cur.close()
        conn.close()