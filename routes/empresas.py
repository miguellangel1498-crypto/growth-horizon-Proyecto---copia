from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Empresa, Sector, Usuario
from models.roles import ROL_EMPRESA, ROL_EMPLEADO
from routes.decoradores import superadmin_requerido

empresas_bp = Blueprint("empresas", __name__, url_prefix="/empresas")


@empresas_bp.route("/")
@login_required
@superadmin_requerido
def listar():
    sector_id = request.args.get("sector", type=int)
    busqueda = request.args.get("q", "").strip()

    consulta = Empresa.query

    if sector_id:
        consulta = consulta.filter(Empresa.sector_id == sector_id)
    if busqueda:
        consulta = consulta.filter(
            db.or_(
                Empresa.nombre.ilike(f"%{busqueda}%"),
                Empresa.ruc.ilike(f"%{busqueda}%"),
                Empresa.actividad.ilike(f"%{busqueda}%"),
            )
        )

    empresas = consulta.order_by(Empresa.nombre.asc()).all()
    sectores = Sector.query.order_by(Sector.nombre.asc()).all()
    sector_seleccionado = db.session.get(Sector, sector_id) if sector_id else None

    return render_template(
        "empresas/listar.html",
        empresas=empresas,
        sectores=sectores,
        sector_seleccionado=sector_seleccionado,
        busqueda=busqueda,
    )


@empresas_bp.route("/<int:empresa_id>")
@login_required
@superadmin_requerido
def detalle(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    usuarios = [u for u in empresa.usuarios if u.activo]
    total_empleados = sum(1 for u in usuarios if u.rol == ROL_EMPLEADO)

    from models import IndiceMadurez

    ultimo_indice = (
        IndiceMadurez.query
        .filter_by(empresa_id=empresa.id)
        .order_by(IndiceMadurez.fecha.desc())
        .first()
    )

    return render_template(
        "empresas/detalle.html",
        empresa=empresa,
        usuarios=usuarios,
        total_empleados=total_empleados,
        ultimo_indice=ultimo_indice,
    )


@empresas_bp.route("/nueva", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def nueva():
    sectores = Sector.query.order_by(Sector.nombre.asc()).all()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        ruc = request.form.get("ruc", "").strip() or None
        sector_id = request.form.get("sector_id", type=int) or None
        actividad = request.form.get("actividad", "").strip() or None
        correo = request.form.get("correo", "").strip() or None
        telefono = request.form.get("telefono", "").strip() or None
        direccion = request.form.get("direccion", "").strip() or None
        sitio_web = request.form.get("sitio_web", "").strip() or None
        estado = request.form.get("estado", "activo")
        tamano_empresa = request.form.get("tamano_empresa", "PEQUENA")

        if not nombre:
            flash("El nombre de la empresa es obligatorio.", "error")
            return render_template("empresas/form.html", sectores=sectores, empresa=None)

        if ruc and Empresa.query.filter_by(ruc=ruc).first():
            flash("Ya existe una empresa con ese RUC.", "error")
            return render_template("empresas/form.html", sectores=sectores, empresa=None)

        empresa = Empresa(
            nombre=nombre,
            ruc=ruc,
            sector_id=sector_id,
            actividad=actividad,
            correo=correo,
            telefono=telefono,
            direccion=direccion,
            sitio_web=sitio_web,
            estado=estado,
            tamano_empresa=tamano_empresa,
        )
        db.session.add(empresa)
        db.session.commit()

        flash(f"Empresa '{empresa.nombre}' creada correctamente.", "success")
        return redirect(url_for("empresas.listar"))

    return render_template("empresas/form.html", sectores=sectores, empresa=None)


@empresas_bp.route("/<int:empresa_id>/editar", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def editar(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    sectores = Sector.query.order_by(Sector.nombre.asc()).all()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        ruc = request.form.get("ruc", "").strip() or None
        sector_id = request.form.get("sector_id", type=int) or None

        if not nombre:
            flash("El nombre de la empresa es obligatorio.", "error")
            return render_template("empresas/form.html", sectores=sectores, empresa=empresa)

        if ruc:
            duplicado = Empresa.query.filter(Empresa.ruc == ruc, Empresa.id != empresa.id).first()
            if duplicado:
                flash("Ya existe otra empresa con ese RUC.", "error")
                return render_template("empresas/form.html", sectores=sectores, empresa=empresa)

        empresa.nombre = nombre
        empresa.ruc = ruc
        empresa.sector_id = sector_id
        empresa.actividad = request.form.get("actividad", "").strip() or None
        empresa.correo = request.form.get("correo", "").strip() or None
        empresa.telefono = request.form.get("telefono", "").strip() or None
        empresa.direccion = request.form.get("direccion", "").strip() or None
        empresa.sitio_web = request.form.get("sitio_web", "").strip() or None
        empresa.estado = request.form.get("estado", "activo")
        empresa.tamano_empresa = request.form.get("tamano_empresa", empresa.tamano_empresa)

        db.session.commit()
        flash(f"Empresa '{empresa.nombre}' actualizada correctamente.", "success")
        return redirect(url_for("empresas.listar"))

    return render_template("empresas/form.html", sectores=sectores, empresa=empresa)


@empresas_bp.route("/<int:empresa_id>/eliminar", methods=["POST"])
@login_required
@superadmin_requerido
def eliminar(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    nombre = empresa.nombre
    db.session.delete(empresa)
    db.session.commit()
    flash(f"Empresa '{nombre}' eliminada.", "info")
    return redirect(url_for("empresas.listar"))
