import os
from decimal import Decimal

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

APP_BASE_PATH: str = os.getenv("APP_BASE_PATH", "/ext/rodel-stocks")
APP_MENU_URL = os.getenv("APP_MENU_URL", "/")
LOGOUT_URL = os.getenv("LOGOUT_URL", f"{APP_BASE_PATH}/logout")
LOGIN_FALLBACK_URL = os.getenv("LOGIN_FALLBACK_URL", "/")
SESSION_CHECK_URL = os.getenv("SESSION_CHECK_URL", f"{APP_BASE_PATH}/session-check")

STOCKS_MYSQL_HOST = os.getenv("STOCKS_MYSQL_HOST", "mysql")
STOCKS_MYSQL_PORT = int(os.getenv("STOCKS_MYSQL_PORT", "3306"))
STOCKS_MYSQL_USER = os.getenv("STOCKS_MYSQL_USER", "proyecto_user")
STOCKS_MYSQL_PASSWORD = os.getenv("STOCKS_MYSQL_PASSWORD", "")
STOCKS_MYSQL_DATABASE = os.getenv("STOCKS_MYSQL_DATABASE", "stocks_db")
DB_MAX_RETRIES = int(os.getenv("DB_MAX_RETRIES", "30"))
DB_RETRY_DELAY = int(os.getenv("DB_RETRY_DELAY", "2"))

# Control Plane / Portal (app-hija-1)
CONTROL_PLANE_BASE_URL = os.getenv("CONTROL_PLANE_BASE_URL")
CONTROL_PLANE_TIMEOUT = float(os.getenv("CONTROL_PLANE_TIMEOUT", "1.0"))
CONTROL_PLANE_READ_TIMEOUT = float(os.getenv("CONTROL_PLANE_READ_TIMEOUT", "3.0"))

QTY_PRECISION = Decimal("0.001")
