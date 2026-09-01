import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _default_db_path():
    directorio = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
    os.makedirs(directorio, exist_ok=True)
    return os.path.join(directorio, "growth_horizon.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "growth-horizon-dev-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///" + _default_db_path())
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Sesiones ──────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "gh_session"

    # ── Cookie "Recuérdame" ───────────────────────────────────
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    WTF_CSRF_ENABLED = True