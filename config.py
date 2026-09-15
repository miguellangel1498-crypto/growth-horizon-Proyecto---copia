import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "growth-horizon-dev-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root@localhost/growthhorizon?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Sesiones ──────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "gh_session"

    # ── Cookie "Recuerdame" ───────────────────────────────────
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    WTF_CSRF_ENABLED = True
