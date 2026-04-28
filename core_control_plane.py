import requests
from fastapi import Request

from core_config import CONTROL_PLANE_BASE_URL, CONTROL_PLANE_TIMEOUT, CONTROL_PLANE_READ_TIMEOUT


def _extract_jwt_token(request: Request, authorization: str | None = None) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1].strip()

    header_auth = request.headers.get("authorization")
    if header_auth and header_auth.startswith("Bearer "):
        return header_auth.split(" ", 1)[1].strip()

    raw_cookie = request.cookies.get("jwt")
    if raw_cookie:
        return raw_cookie.strip()

    return None


def _build_auth_transport(
    request: Request,
    app_id: int,
    client_id: int,
    authorization: str | None = None,
) -> tuple[dict, dict | None]:
    jwt_token = _extract_jwt_token(request, authorization)

    headers = {
        "X-App-Id": str(app_id),
        "X-Client-Id": str(client_id),
    }

    cookies = None

    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"
        cookies = {"jwt": jwt_token}

    return headers, cookies


def _safe_get_json(
    path: str,
    request: Request,
    app_id: int,
    client_id: int,
    authorization: str | None = None,
) -> dict:
    headers, cookies = _build_auth_transport(
        request=request,
        app_id=app_id,
        client_id=client_id,
        authorization=authorization,
    )

    try:
        response = requests.get(
            f"{CONTROL_PLANE_BASE_URL}{path}",
            headers=headers,
            cookies=cookies,
            timeout=(CONTROL_PLANE_TIMEOUT, CONTROL_PLANE_READ_TIMEOUT),
        )

        if response.status_code == 200:
            payload = response.json()
            if isinstance(payload, dict):
                return payload

        print(
            f"[control-plane {path}] status={response.status_code} "
            f"body={response.text[:300]}"
        )

    except Exception as exc:
        print(f"[control-plane {path}] exception: {exc}")

    return {}


def get_context_info(
    request: Request,
    app_id: int,
    client_id: int,
    authorization: str | None = None,
) -> dict:
    """
    Compatibilidad histórica:
    obtiene contexto mínimo desde /internal/context-info
    """
    return _safe_get_json(
        path="/internal/context-info",
        request=request,
        app_id=app_id,
        client_id=client_id,
        authorization=authorization,
    )


def get_session_context(
    request: Request,
    app_id: int,
    client_id: int,
    authorization: str | None = None,
) -> dict:
    """
    Nuevo contrato estándar para apps hijas:
    obtiene contexto + rol contextual desde /public/session-context
    """
    return _safe_get_json(
        path="/public/session-context",
        request=request,
        app_id=app_id,
        client_id=client_id,
        authorization=authorization,
    )
