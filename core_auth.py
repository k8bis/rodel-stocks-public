import jwt
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from core_config import SECRET_KEY, ALGORITHM, LOGIN_FALLBACK_URL
from core_db import db_connection
from core_helpers import render_page


router = APIRouter()


def get_user_from_request(request: Request, authorization: str | None = None) -> str | None:
    token = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if not token:
        token = request.cookies.get("jwt")

    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def resolve_context(request: Request, x_app_id: int | None, x_client_id: int | None):
    app_id = x_app_id
    client_id = x_client_id

    if app_id is None:
        q = request.query_params.get("app_id")
        if q and q.isdigit():
            app_id = int(q)

    if client_id is None:
        q = request.query_params.get("client_id")
        if q and q.isdigit():
            client_id = int(q)

    return app_id, client_id


def require_auth_context(
    request: Request,
    authorization: str | None,
    x_app_id: int | None,
    x_client_id: int | None,
):
    user = get_user_from_request(request, authorization)
    if not user:
        raise HTTPException(status_code=401, detail="No token")

    app_id, client_id = resolve_context(request, x_app_id, x_client_id)
    if not app_id or not client_id:
        raise HTTPException(status_code=400, detail="Faltan app_id o client_id")

    return user, app_id, client_id


@router.get("/health")
def health():
    try:
        conn = db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "ok", "service": "rodel-stocks", "db": "ok"}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "service": "rodel-stocks", "db": str(exc)},
        )


@router.get("/")
def root(
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_id: int | None = Header(alias="X-App-Id", default=None),
    x_client_id: int | None = Header(alias="X-Client-Id", default=None),
):
    user = get_user_from_request(request, authorization)
    if not user:
        return RedirectResponse(url=LOGIN_FALLBACK_URL, status_code=302)

    app_id, client_id = resolve_context(request, x_app_id, x_client_id)
    if not app_id or not client_id:
        raise HTTPException(status_code=400, detail="Faltan app_id o client_id")

    return render_page(
        request=request,
        user=user,
        app_id=app_id,
        client_id=client_id,
        authorization=authorization,
    )


@router.get("/entry")
def entry(
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_id: int | None = Header(alias="X-App-Id", default=None),
    x_client_id: int | None = Header(alias="X-Client-Id", default=None),
):
    user = get_user_from_request(request, authorization)
    if not user:
        return RedirectResponse(url=LOGIN_FALLBACK_URL, status_code=302)

    app_id, client_id = resolve_context(request, x_app_id, x_client_id)
    if not app_id or not client_id:
        raise HTTPException(status_code=400, detail="Faltan app_id o client_id")

    return {"ok": True, "user": user, "app_id": app_id, "client_id": client_id}


@router.get("/session-check")
def session_check(
    request: Request,
    authorization: str | None = Header(default=None),
):
    user = get_user_from_request(request, authorization)
    if not user:
        return RedirectResponse(url=LOGIN_FALLBACK_URL, status_code=302)
    return {"ok": True}


@router.post("/logout")
def logout():
    response = RedirectResponse(url=LOGIN_FALLBACK_URL, status_code=302)
    response.delete_cookie("jwt", path="/")
    return response
