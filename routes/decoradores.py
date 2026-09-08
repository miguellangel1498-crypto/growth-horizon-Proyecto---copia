from functools import wraps

from flask import abort
from flask_login import current_user

from models.roles import ROL_EMPLEADO, ROL_EMPRESA, ROL_SUPERADMIN


def _sin_acceso():
    abort(403)


def superadmin_requerido(func):
    """Solo el Superadministrador puede acceder."""
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != ROL_SUPERADMIN:
            _sin_acceso()
        return func(*args, **kwargs)

    return envoltura


def admin_empresa_requerido(func):
    """Solo el Administrador de Empresa puede acceder (no el empleado)."""
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated:
            _sin_acceso()
        if current_user.rol != ROL_EMPRESA:
            _sin_acceso()
        if not current_user.activo:
            _sin_acceso()
        if current_user.empresa is not None and not current_user.acceso_empresa_activa:
            _sin_acceso()
        return func(*args, **kwargs)

    return envoltura


def empleado_requerido(func):
    """Solo el Empleado/Vendedor puede acceder (no el admin ni el superadmin)."""
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated:
            _sin_acceso()
        if current_user.rol != ROL_EMPLEADO:
            _sin_acceso()
        if not current_user.activo:
            _sin_acceso()
        if current_user.empresa is None or not current_user.acceso_empresa_activa:
            _sin_acceso()
        return func(*args, **kwargs)

    return envoltura


def miembro_empresa_requerido(func):
    """Admin Empresa O Empleado — ambos deben tener empresa asignada y activa."""
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated:
            _sin_acceso()
        if current_user.empresa is None:
            _sin_acceso()
        if not current_user.activo:
            _sin_acceso()
        if not current_user.acceso_empresa_activa:
            _sin_acceso()
        return func(*args, **kwargs)

    return envoltura


# Alias para retrocompatibilidad
def requiere_empresa(func):
    return miembro_empresa_requerido(func)


def empleado_o_admin_requerido(func):
    """Admin Empresa O Empleado — cualquiera de los dos roles de empresa."""
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated:
            _sin_acceso()
        if current_user.rol not in (ROL_EMPLEADO, ROL_EMPRESA):
            _sin_acceso()
        if not current_user.activo:
            _sin_acceso()
        if current_user.empresa is None or not current_user.acceso_empresa_activa:
            _sin_acceso()
        return func(*args, **kwargs)

    return envoltura


def acceso_empresa_activa_requerido(func):
    """Verifica que la empresa del usuario esté activa."""
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated:
            _sin_acceso()
        if not current_user.activo:
            _sin_acceso()
        if current_user.empresa is not None and not current_user.acceso_empresa_activa:
            _sin_acceso()
        return func(*args, **kwargs)

    return envoltura
