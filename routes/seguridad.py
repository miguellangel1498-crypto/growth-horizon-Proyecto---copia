from flask import Blueprint, render_template, request
from flask_login import login_required

from models import Auditoria, Usuario
from routes.decoradores import superadmin_requerido

seguridad_bp = Blueprint("seguridad", __name__, url_prefix="/seguridad")


@seguridad_bp.route("/auditoria")
@login_required
@superadmin_requerido
def auditoria():
    pagina = request.args.get("page", 1, type=int)
    accion = request.args.get("accion", "").strip()
    email = request.args.get("usuario", "").strip()

    consulta = Auditoria.query.outerjoin(Usuario, Auditoria.usuario_id == Usuario.id)

    if accion:
        consulta = consulta.filter(Auditoria.accion == accion)
    if email:
        consulta = consulta.filter(Usuario.email.ilike(f"%{email}%"))

    registros = consulta.order_by(Auditoria.created_at.desc()).paginate(
        page=pagina, per_page=20, error_out=False
    )
    acciones = [r[0] for r in (Auditoria.query.with_entities(Auditoria.accion).distinct().all())]
    acciones.sort()

    return render_template(
        "seguridad/auditoria.html",
        registros=registros,
        acciones=acciones,
        accion=accion,
        email=email,
    )
