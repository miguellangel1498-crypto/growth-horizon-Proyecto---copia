from functools import wraps

from flask import abort
from flask_login import current_user


def admin_requerido(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.rol == "admin":
            abort(403)
        return func(*args, **kwargs)

    return envoltura


def requiere_empresa(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated or current_user.empresa is None:
            abort(403)
        return func(*args, **kwargs)

    return envoltura