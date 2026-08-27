from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Configuracion, Empresa, Usuario
from models.roles import (
    ESTADO_EMPRESA_ACTIVO,
    ESTADO_EMPRESA_INACTIVO,
    ESTADO_EMPRESA_PENDIENTE,
    ESTADO_EMPRESA_RECHAZADO,
    ESTADOS_EMPRESA,
    MATRIZ_PERMISOS,
    ROL_EMPLEADO,
    ROL_EMPRESA,
)
from routes.decoradores import superadmin_requerido
from services.auditoria import registrar_y_commit

superadmin_bp = Blueprint("superadmin", __name__, url_prefix="/superadmin")


def _empresa_o_404(empresa_id):
    return Empresa.query.get_or_404(empresa_id)


@superadmin_bp.route("/")
@login_required
@superadmin_requerido
def panel():
    total_empresas = Empresa.query.count()
    empresas_pendientes = Empresa.query.filter_by(estado=ESTADO_EMPRESA_PENDIENTE).count()
    empresas_activas = Empresa.query.filter_by(estado=ESTADO_EMPRESA_ACTIVO).count()
    total_usuarios = Usuario.query.count()
    total_admins_empresa = Usuario.query.filter_by(rol=ROL_EMPRESA).count()
    total_empleados = Usuario.query.filter_by(rol=ROL_EMPLEADO).count()
    empresas_recientes = Empresa.query.order_by(Empresa.created_at.desc()).limit(5).all()

    return render_template(
        "superadmin/panel.html",
        total_empresas=total_empresas,
        empresas_pendientes=empresas_pendientes,
        empresas_activas=empresas_activas,
        total_usuarios=total_usuarios,
        total_admins_empresa=total_admins_empresa,
        total_empleados=total_empleados,
        empresas_recientes=empresas_recientes,
    )


@superadmin_bp.route("/empresas")
@login_required
@superadmin_requerido
def empresas():
    estado = request.args.get("estado", "").strip()
    busqueda = request.args.get("q", "").strip()

    consulta = Empresa.query
    if estado in ESTADOS_EMPRESA:
        consulta = consulta.filter(Empresa.estado == estado)
    if busqueda:
        consulta = consulta.filter(
            db.or_(
                Empresa.nombre.ilike(f"%{busqueda}%"),
                Empresa.ruc.ilike(f"%{busqueda}%"),
            )
        )

    empresas = consulta.order_by(Empresa.nombre.asc()).all()
    return render_template(
        "superadmin/empresas.html",
        empresas=empresas,
        estado=estado,
        busqueda=busqueda,
        estados=ESTADOS_EMPRESA,
    )


@superadmin_bp.route("/empresas/pendientes")
@login_required
@superadmin_requerido
def empresas_pendientes():
    empresas = Empresa.query.filter_by(estado=ESTADO_EMPRESA_PENDIENTE).order_by(Empresa.created_at.asc()).all()
    return render_template("superadmin/empresas_pendientes.html", empresas=empresas)


@superadmin_bp.route("/empresas/<int:empresa_id>/aprobar", methods=["POST"])
@login_required
@superadmin_requerido
def aprobar_empresa(empresa_id):
    empresa = _empresa_o_404(empresa_id)
    empresa.estado = ESTADO_EMPRESA_ACTIVO
    empresa.notas_admin = request.form.get("notas_admin", empresa.notas_admin) or None
    db.session.commit()
    registrar_y_commit("EMPRESA_APROBADA", entidad="Empresa", entidad_id=empresa.id,
                       detalle=f"Empresa {empresa.nombre} aprobada por {current_user.email}")
    flash(f"La empresa '{empresa.nombre}' fue aprobada y ya tiene acceso.", "success")
    return redirect(url_for("superadmin.empresas_pendientes"))


@superadmin_bp.route("/empresas/<int:empresa_id>/rechazar", methods=["POST"])
@login_required
@superadmin_requerido
def rechazar_empresa(empresa_id):
    empresa = _empresa_o_404(empresa_id)
    empresa.estado = ESTADO_EMPRESA_RECHAZADO
    empresa.notas_admin = request.form.get("motivo", "").strip() or None
    db.session.commit()
    registrar_y_commit("EMPRESA_RECHAZADA", entidad="Empresa", entidad_id=empresa.id,
                       detalle=f"Empresa {empresa.nombre} rechazada por {current_user.email}")
    flash(f"La empresa '{empresa.nombre}' fue rechazada.", "warning")
    return redirect(url_for("superadmin.empresas_pendientes"))


@superadmin_bp.route("/empresas/<int:empresa_id>/suspender", methods=["POST"])
@login_required
@superadmin_requerido
def suspender_empresa(empresa_id):
    empresa = _empresa_o_404(empresa_id)
    if empresa.estado == ESTADO_EMPRESA_PENDIENTE:
        abort(400)
    empresa.estado = ESTADO_EMPRESA_INACTIVO
    db.session.commit()
    registrar_y_commit("EMPRESA_SUSPENDIDA", entidad="Empresa", entidad_id=empresa.id,
                       detalle=f"Empresa {empresa.nombre} suspendida por {current_user.email}")
    flash(f"La empresa '{empresa.nombre}' fue suspendida.", "info")
    return redirect(url_for("superadmin.empresas"))


@superadmin_bp.route("/empresas/<int:empresa_id>/activar", methods=["POST"])
@login_required
@superadmin_requerido
def activar_empresa(empresa_id):
    empresa = _empresa_o_404(empresa_id)
    empresa.estado = ESTADO_EMPRESA_ACTIVO
    db.session.commit()
    registrar_y_commit("EMPRESA_ACTIVADA", entidad="Empresa", entidad_id=empresa.id,
                       detalle=f"Empresa {empresa.nombre} reactivada por {current_user.email}")
    flash(f"La empresa '{empresa.nombre}' fue activada nuevamente.", "success")
    return redirect(url_for("superadmin.empresas"))


@superadmin_bp.route("/empresas/<int:empresa_id>")
@login_required
@superadmin_requerido
def detalle_empresa(empresa_id):
    empresa = _empresa_o_404(empresa_id)
    from models import HorarioAtencion, Producto, Venta

    productos = Producto.query.filter_by(empresa_id=empresa.id).count()
    horarios = HorarioAtencion.query.filter_by(empresa_id=empresa.id).count()
    ventas = Venta.query.filter_by(empresa_id=empresa.id).count()
    usuarios = (
        Usuario.query.filter(Usuario.empresa_id == empresa.id, Usuario.rol.in_([ROL_EMPRESA, ROL_EMPLEADO]))
        .order_by(Usuario.nombre.asc())
        .all()
    )
    return render_template(
        "superadmin/detalle_empresa.html",
        empresa=empresa,
        productos=productos,
        horarios=horarios,
        ventas=ventas,
        usuarios=usuarios,
    )


@superadmin_bp.route("/permisos", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def permisos():
    if request.method == "POST":
        claves = [
            "registro_empresas_abierto",
            "requiere_aprobacion_empresa",
            "permitir_registro_personas",
        ]
        for clave in claves:
            valor = "on" if request.form.get(clave) else "off"
            Configuracion.poner(clave, valor)
        db.session.commit()
        flash("La configuración de permisos globales fue actualizada.", "success")
        return redirect(url_for("superadmin.permisos"))

    toggles = {
        "registro_empresas_abierto": Configuracion.boolean("registro_empresas_abierto", True),
        "requiere_aprobacion_empresa": Configuracion.boolean("requiere_aprobacion_empresa", True),
        "permitir_registro_personas": Configuracion.boolean("permitir_registro_personas", True),
    }
    return render_template(
        "superadmin/permisos.html",
        toggles=toggles,
        matriz=MATRIZ_PERMISOS,
        roles=["superadmin", "empresa", "empleado", "analista"],
    )
