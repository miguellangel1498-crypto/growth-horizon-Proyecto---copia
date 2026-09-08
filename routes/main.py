from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Auditoria, Empresa, Sector
from models.roles import ROL_EMPLEADO, ROL_EMPRESA, ROL_SUPERADMIN

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Enrutador central: redirige a cada usuario a su portal exclusivo según su rol.
    - Superadmin  → /superadmin/
    - Admin Empresa → /mi-empresa/
    - Empleado    → /empleado/
    """
    if current_user.rol == ROL_SUPERADMIN:
        return redirect(url_for("superadmin.panel"))

    if current_user.rol == ROL_EMPRESA:
        return redirect(url_for("cliente.panel"))

    if current_user.rol == ROL_EMPLEADO:
        return redirect(url_for("empleado.panel"))

    # Fallback: si el rol es desconocido, mostrar un 403 limpio
    from flask import abort
    abort(403)