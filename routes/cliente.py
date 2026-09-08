from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Auditoria, Usuario
from models.roles import ROL_EMPLEADO, ROL_EMPRESA
from routes.decoradores import admin_empresa_requerido, requiere_empresa

cliente_bp = Blueprint("cliente", __name__, url_prefix="/mi-empresa")


@cliente_bp.route("/")
@login_required
@requiere_empresa
def panel():
    if not current_user.acceso_empresa_activa:
        abort(403)
    empresa = current_user.empresa

    total_empleados = Usuario.query.filter_by(empresa_id=empresa.id, rol=ROL_EMPLEADO).count()
    es_empleado = current_user.es_empleado
    puede_administrar = current_user.puede_administrar
    puede_gestionar_empleados = current_user.puede_gestionar_empleados

    return render_template(
        "cliente/panel.html",
        empresa=empresa,
        total_empleados=total_empleados,
        es_empleado=es_empleado,
        puede_administrar=puede_administrar,
        puede_gestionar_empleados=puede_gestionar_empleados,
    )


def _empresa_id():
    if current_user.empresa is None:
        abort(403)
    if not current_user.acceso_empresa_activa:
        abort(403)
    return current_user.empresa.id


@cliente_bp.route("/empleados")
@login_required
@admin_empresa_requerido
def empleados_listar():
    empresa_id = _empresa_id()
    empleados = (
        Usuario.query.filter_by(empresa_id=empresa_id, rol=ROL_EMPLEADO)
        .order_by(Usuario.nombre.asc())
        .all()
    )
    return render_template("cliente/empleados/listar.html", empleados=empleados, empresa=current_user.empresa)


@cliente_bp.route("/empleados/nuevo", methods=["GET", "POST"])
@login_required
@admin_empresa_requerido
def empleados_nuevo():
    empresa_id = _empresa_id()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        cargo = request.form.get("cargo", "").strip() or None
        password = request.form.get("password", "")
        confirmar = request.form.get("confirmar_password", "")

        errores = []
        if not nombre or not email:
            errores.append("El nombre y el correo son obligatorios.")
        if len(password) < 8:
            errores.append("La contraseña debe tener al menos 8 caracteres.")
        if password != confirmar:
            errores.append("Las contraseñas no coinciden.")
        if Usuario.query.filter_by(email=email).first():
            errores.append("Ya existe una cuenta con ese correo.")

        if errores:
            for e in errores:
                flash(e, "error")
            return render_template("cliente/empleados/form.html", empleado=None)

        empleado = Usuario(
            nombre=nombre,
            email=email,
            rol=ROL_EMPLEADO,
            cargo=cargo,
            empresa_id=empresa_id,
        )
        empleado.set_password(password)
        db.session.add(empleado)
        db.session.commit()

        from services.auditoria import registrar_y_commit

        registrar_y_commit(
            "CREACION_EMPLEADO",
            entidad="Usuario",
            entidad_id=empleado.id,
            detalle=f"Empleado {email} creado para {current_user.empresa.nombre}",
        )

        flash(f"Empleado '{nombre}' registrado correctamente.", "success")
        return redirect(url_for("cliente.empleados_listar"))

    return render_template("cliente/empleados/form.html", empleado=None)


@cliente_bp.route("/empleados/<int:empleado_id>/estado", methods=["POST"])
@login_required
@admin_empresa_requerido
def empleados_cambiar_estado(empleado_id):
    empresa_id = _empresa_id()
    empleado = Usuario.query.filter_by(id=empleado_id, empresa_id=empresa_id, rol=ROL_EMPLEADO).first_or_404()
    empleado.activo = not empleado.activo
    db.session.commit()
    flash(f"El empleado '{empleado.nombre}' ahora está {'activo' if empleado.activo else 'inactivo'}.", "info")
    return redirect(url_for("cliente.empleados_listar"))


@cliente_bp.route("/empleados/<int:empleado_id>/eliminar", methods=["POST"])
@login_required
@admin_empresa_requerido
def empleados_eliminar(empleado_id):
    empresa_id = _empresa_id()
    empleado = Usuario.query.filter_by(id=empleado_id, empresa_id=empresa_id, rol=ROL_EMPLEADO).first_or_404()
    nombre = empleado.nombre
    db.session.delete(empleado)
    db.session.commit()
    flash(f"Empleado '{nombre}' eliminado.", "info")
    return redirect(url_for("cliente.empleados_listar"))


@cliente_bp.route("/seguridad")
@login_required
@admin_empresa_requerido
def seguridad():
    empresa_id = _empresa_id()
    pagina = request.args.get("page", 1, type=int)

    empleado_ids = [u.id for u in Usuario.query.filter_by(empresa_id=empresa_id, rol=ROL_EMPLEADO).all()]
    admin_ids = [u.id for u in Usuario.query.filter_by(empresa_id=empresa_id, rol=ROL_EMPRESA).all()]
    todos_ids = empleado_ids + admin_ids

    consulta = Auditoria.query.filter(
        Auditoria.usuario_id.in_(todos_ids),
        Auditoria.accion.in_(["LOGIN_FALLIDO", "LOGIN_EXITOSO", "ALERTA_SUPERADMIN"]),
    )

    registros = consulta.order_by(Auditoria.created_at.desc()).paginate(
        page=pagina, per_page=20, error_out=False
    )

    empleados_con_fallos = (
        db.session.query(Usuario, db.func.count(Auditoria.id).label("total_fallos"))
        .join(Auditoria, Auditoria.usuario_id == Usuario.id)
        .filter(
            Usuario.empresa_id == empresa_id,
            Usuario.rol == ROL_EMPLEADO,
            Auditoria.accion == "LOGIN_FALLIDO",
        )
        .group_by(Usuario.id)
        .having(db.func.count(Auditoria.id) > 0)
        .order_by(db.desc("total_fallos"))
        .all()
    )

    return render_template(
        "cliente/seguridad.html",
        registros=registros,
        empleados_con_fallos=empleados_con_fallos,
    )
