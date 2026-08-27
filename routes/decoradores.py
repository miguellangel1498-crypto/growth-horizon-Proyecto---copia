from functools import wraps

from flask import abort
from flask_login import current_user

from models.roles import ROL_EMPLEADO, ROL_EMPRESA, ROL_SUPERADMIN


def _sin_acceso():
    abort(403)


def superadmin_requerido(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != ROL_SUPERADMIN:
            _sin_acceso()
        return func(*args, **kwargs)

    return envoltura


def admin_empresa_requerido(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != ROL_EMPRESA:
            _sin_acceso()
        return func(*args, **kwargs)

    return envoltura


def miembro_empresa_requerido(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated or current_user.empresa is None:
            _sin_acceso()
        return func(*args, **kwargs)

    return envoltura


def requiere_empresa(func):
    return miembro_empresa_requerido(func)


def empleado_o_admin_requerido(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated:
            _sin_acceso()
        if current_user.rol not in (ROL_EMPLEADO, ROL_EMPRESA):
            _sin_acceso()
        return func(*args, **kwargs)

    return envoltura


def acceso_empresa_activa_requerido(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated:
            _sin_acceso()
        if current_user.empresa is not None and not current_user.acceso_empresa_activa:
            _sin_acceso()
        return func(*args, **kwargs)

    return envoltura
