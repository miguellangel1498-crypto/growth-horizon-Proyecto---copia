from flask import Blueprint, render_template
from flask_login import current_user, login_required

from routes.decoradores import empleado_requerido

empleado_bp = Blueprint("empleado", __name__, url_prefix="/empleado")


@empleado_bp.route("/")
@login_required
@empleado_requerido
def panel():
    empresa = current_user.empresa
    return render_template(
        "empleado/panel.html",
        empresa=empresa,
    )
