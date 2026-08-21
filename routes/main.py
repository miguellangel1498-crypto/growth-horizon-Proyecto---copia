from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Auditoria, Empresa, Sector

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.es_empresa:
        return redirect(url_for("cliente.panel"))

    total_empresas = Empresa.query.count()
    total_sectores = Sector.query.count()
    empresas_por_sector = (
        db.session.query(Sector.nombre, db.func.count(Empresa.id))
        .outerjoin(Empresa, Empresa.sector_id == Sector.id)
        .group_by(Sector.id)
        .order_by(db.func.count(Empresa.id).desc())
        .all()
    )
    ultimas_auditorias = Auditoria.query.order_by(Auditoria.created_at.desc()).limit(5).all()

    return render_template(
        "main/dashboard.html",
        total_empresas=total_empresas,
        total_sectores=total_sectores,
        empresas_por_sector=empresas_por_sector,
        ultimas_auditorias=ultimas_auditorias,
    )