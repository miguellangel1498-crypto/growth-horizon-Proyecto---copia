from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from extensions import db
from models import DIAS_SEMANA, HorarioAtencion, Producto, Usuario, Venta
from models.roles import ROL_EMPLEADO, ROL_EMPRESA
from routes.decoradores import admin_empresa_requerido, requiere_empresa
from services.exporter import exportar_inventario, exportar_ventas

cliente_bp = Blueprint("cliente", __name__, url_prefix="/mi-empresa")


@cliente_bp.route("/")
@login_required
@requiere_empresa
def panel():
    if not current_user.acceso_empresa_activa:
        abort(403)
    empresa = current_user.empresa
    productos = Producto.query.filter_by(empresa_id=empresa.id).order_by(Producto.nombre.asc()).all()
    horarios = HorarioAtencion.query.filter_by(empresa_id=empresa.id).order_by(HorarioAtencion.dia_numero.asc()).all()
    ventas = Venta.query.filter_by(empresa_id=empresa.id).order_by(Venta.fecha.desc()).limit(8).all()
    total_ventas = sum(v.total for v in Venta.query.filter_by(empresa_id=empresa.id).all()) if current_user.puede_ver_finanzas else 0

    total_productos = len(productos)
    total_horarios = len(horarios)
    total_ventas_registradas = Venta.query.filter_by(empresa_id=empresa.id).count()
    es_empleado = current_user.es_empleado
    puede_ver_finanzas = current_user.puede_ver_finanzas
    puede_administrar = current_user.puede_administrar
    puede_gestionar_empleados = current_user.puede_gestionar_empleados

    pasos = [
        {"titulo": "Agrega tu primer producto", "descripcion": "Da de alta lo que vendes para empezar a medir.", "hecho": total_productos > 0, "url": url_for("cliente.productos_nuevo")},
        {"titulo": "Configura tus horarios", "descripcion": "Define cuándo atiendes a tus clientes.", "hecho": total_horarios > 0, "url": url_for("cliente.horarios_nuevo")},
        {"titulo": "Registra tu primera venta", "descripcion": "Empieza a ver métricas y análisis en vivo.", "hecho": total_ventas_registradas > 0, "url": url_for("cliente.ventas_nueva")},
    ]
    pasos_completados = sum(1 for p in pasos if p["hecho"])
    progreso = int((pasos_completados / len(pasos)) * 100)
    es_nuevo = pasos_completados == 0

    return render_template(
        "cliente/panel.html",
        empresa=empresa,
        productos=productos,
        horarios=horarios,
        ventas=ventas,
        total_ventas=total_ventas,
        total_productos=total_productos,
        total_horarios=total_horarios,
        total_ventas_registradas=total_ventas_registradas,
        pasos=pasos,
        pasos_completados=pasos_completados,
        progreso=progreso,
        es_nuevo=es_nuevo,
        es_empleado=es_empleado,
        puede_ver_finanzas=puede_ver_finanzas,
        puede_administrar=puede_administrar,
        puede_gestionar_empleados=puede_gestionar_empleados,
    )


def _espectiva_empresa():
    if current_user.empresa is None:
        abort(403)
    if not current_user.acceso_empresa_activa:
        abort(403)
    return current_user.empresa.id


@cliente_bp.route("/productos")
@login_required
@requiere_empresa
def productos_listar():
    empresa_id = _espectiva_empresa()
    busqueda = request.args.get("q", "").strip()
    consulta = Producto.query.filter_by(empresa_id=empresa_id)
    if busqueda:
        consulta = consulta.filter(
            db.or_(Producto.nombre.ilike(f"%{busqueda}%"), Producto.categoria.ilike(f"%{busqueda}%"))
        )
    productos = consulta.order_by(Producto.nombre.asc()).all()
    return render_template("cliente/productos/listar.html", productos=productos, busqueda=busqueda)


@cliente_bp.route("/productos/nuevo", methods=["GET", "POST"])
@login_required
@admin_empresa_requerido
def productos_nuevo():
    empresa_id = _espectiva_empresa()
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip() or None
        precio = request.form.get("precio", "").strip()

        errores = []
        if not nombre:
            errores.append("El nombre del producto es obligatorio.")
        try:
            precio = float(precio)
        except ValueError:
            errores.append("El precio debe ser un número válido.")

        if errores:
            for e in errores:
                flash(e, "error")
            return render_template("cliente/productos/form.html", producto=None)

        db.session.add(Producto(empresa_id=empresa_id, nombre=nombre, categoria=categoria, precio=precio))
        db.session.commit()
        flash("Producto creado correctamente.", "success")
        return redirect(url_for("cliente.productos_listar"))

    return render_template("cliente/productos/form.html", producto=None)


@cliente_bp.route("/productos/<int:producto_id>/editar", methods=["GET", "POST"])
@login_required
@admin_empresa_requerido
def productos_editar(producto_id):
    empresa_id = _espectiva_empresa()
    producto = Producto.query.filter_by(id=producto_id, empresa_id=empresa_id).first_or_404()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip() or None
        precio = request.form.get("precio", "").strip()

        errores = []
        if not nombre:
            errores.append("El nombre del producto es obligatorio.")
        try:
            precio = float(precio)
        except ValueError:
            errores.append("El precio debe ser un número válido.")

        if errores:
            for e in errores:
                flash(e, "error")
            return render_template("cliente/productos/form.html", producto=producto)

        producto.nombre = nombre
        producto.categoria = categoria
        producto.precio = precio
        db.session.commit()
        flash("Producto actualizado correctamente.", "success")
        return redirect(url_for("cliente.productos_listar"))

    return render_template("cliente/productos/form.html", producto=producto)


@cliente_bp.route("/productos/<int:producto_id>/eliminar", methods=["POST"])
@login_required
@admin_empresa_requerido
def productos_eliminar(producto_id):
    empresa_id = _espectiva_empresa()
    producto = Producto.query.filter_by(id=producto_id, empresa_id=empresa_id).first_or_404()
    db.session.delete(producto)
    db.session.commit()
    flash(f"Producto '{producto.nombre}' eliminado.", "info")
    return redirect(url_for("cliente.productos_listar"))


@cliente_bp.route("/horarios")
@login_required
@requiere_empresa
def horarios_listar():
    empresa_id = _espectiva_empresa()
    horarios = HorarioAtencion.query.filter_by(empresa_id=empresa_id).order_by(HorarioAtencion.dia_numero.asc()).all()
    return render_template("cliente/horarios/listar.html", horarios=horarios)


@cliente_bp.route("/horarios/nuevo", methods=["GET", "POST"])
@login_required
@admin_empresa_requerido
def horarios_nuevo():
    empresa_id = _espectiva_empresa()
    if request.method == "POST":
        dia = request.form.get("dia", "").strip()
        apertura = request.form.get("apertura", "").strip() or "09:00"
        cierre = request.form.get("cierre", "").strip() or "18:00"

        numero = next((n for n, d in DIAS_SEMANA if d == dia), 0)
        existe = HorarioAtencion.query.filter_by(empresa_id=empresa_id, dia=dia).first()
        if existe:
            flash("Ya existe un horario configurado para ese día.", "error")
            return render_template("cliente/horarios/form.html", horario=None)

        db.session.add(HorarioAtencion(empresa_id=empresa_id, dia=dia, dia_numero=numero, apertura=apertura, cierre=cierre))
        db.session.commit()
        flash(f"Horario de {dia} guardado.", "success")
        return redirect(url_for("cliente.horarios_listar"))

    return render_template("cliente/horarios/form.html", horario=None)


@cliente_bp.route("/horarios/<int:horario_id>/eliminar", methods=["POST"])
@login_required
@admin_empresa_requerido
def horarios_eliminar(horario_id):
    empresa_id = _espectiva_empresa()
    horario = HorarioAtencion.query.filter_by(id=horario_id, empresa_id=empresa_id).first_or_404()
    db.session.delete(horario)
    db.session.commit()
    flash(f"Horario de {horario.dia} eliminado.", "info")
    return redirect(url_for("cliente.horarios_listar"))


@cliente_bp.route("/ventas")
@login_required
@requiere_empresa
def ventas_listar():
    empresa_id = _espectiva_empresa()
    ventas = Venta.query.filter_by(empresa_id=empresa_id).order_by(Venta.fecha.desc()).all()
    mostrar_finanzas = current_user.puede_ver_finanzas
    total_general = sum(v.total for v in ventas) if mostrar_finanzas else 0
    return render_template("cliente/ventas/listar.html", ventas=ventas, total_general=total_general, mostrar_finanzas=mostrar_finanzas)


@cliente_bp.route("/ventas/nueva", methods=["GET", "POST"])
@login_required
@requiere_empresa
def ventas_nueva():
    empresa_id = _espectiva_empresa()
    productos = Producto.query.filter_by(empresa_id=empresa_id).order_by(Producto.nombre.asc()).all()

    if request.method == "POST":
        producto_id = request.form.get("producto_id", type=int)
        cantidad = request.form.get("cantidad", "1").strip()
        fecha = request.form.get("fecha", "").strip()

        producto = Producto.query.filter_by(id=producto_id, empresa_id=empresa_id).first() if producto_id else None
        if producto is None:
            flash("Selecciona un producto válido.", "error")
            return render_template("cliente/ventas/form.html", productos=productos, DIAS_SEMANA=DIAS_SEMANA)

        try:
            cantidad = int(cantidad)
        except ValueError:
            cantidad = 1

        momento = datetime.utcnow()
        if fecha:
            try:
                momento = datetime.strptime(fecha, "%Y-%m-%dT%H:%M")
            except ValueError:
                pass

        db.session.add(
            Venta(
                empresa_id=empresa_id,
                producto_id=producto.id,
                cantidad=max(cantidad, 1),
                precio_unitario=producto.precio,
                fecha=momento,
            )
        )
        db.session.commit()
        flash("Venta registrada correctamente.", "success")
        return redirect(url_for("cliente.ventas_listar"))

    return render_template("cliente/ventas/form.html", productos=productos, DIAS_SEMANA=DIAS_SEMANA)


@cliente_bp.route("/exportar/ventas")
@login_required
@admin_empresa_requerido
def exportar_ventas_xlsx():
    empresa_id = _espectiva_empresa()
    ventas = Venta.query.filter_by(empresa_id=empresa_id).order_by(Venta.fecha.desc()).all()

    filas = [
        (
            venta.id,
            venta.empresa.nombre if venta.empresa else "—",
            venta.producto.nombre if venta.producto else "—",
            venta.producto.categoria if venta.producto else "—",
            venta.cantidad,
            float(venta.precio_unitario or 0),
            float(venta.total),
            venta.fecha.strftime("%d/%m/%Y %H:%M"),
        )
        for venta in ventas
    ]

    return send_file(
        exportar_ventas(filas),
        as_attachment=True,
        download_name="reporte_ventas.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@cliente_bp.route("/exportar/inventario")
@login_required
@admin_empresa_requerido
def exportar_inventario_xlsx():
    empresa_id = _espectiva_empresa()
    productos = Producto.query.filter_by(empresa_id=empresa_id).order_by(Producto.nombre.asc()).all()

    filas = []
    for producto in productos:
        unidades = db.session.query(db.func.sum(Venta.cantidad)).filter(Venta.producto_id == producto.id).scalar() or 0
        ingresos = db.session.query(db.func.sum(Venta.precio_unitario * Venta.cantidad)).filter(
            Venta.producto_id == producto.id
        ).scalar() or 0
        filas.append(
            (
                producto.id,
                producto.empresa.nombre if producto.empresa else "—",
                producto.nombre,
                producto.categoria or "—",
                float(producto.precio or 0),
                int(unidades),
                float(ingresos),
            )
        )

    return send_file(
        exportar_inventario(filas),
        as_attachment=True,
        download_name="reporte_inventario.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@cliente_bp.route("/ventas/<int:venta_id>/eliminar", methods=["POST"])
@login_required
@admin_empresa_requerido
def ventas_eliminar(venta_id):
    empresa_id = _espectiva_empresa()
    venta = Venta.query.filter_by(id=venta_id, empresa_id=empresa_id).first_or_404()
    db.session.delete(venta)
    db.session.commit()
    flash("Venta eliminada.", "info")
    return redirect(url_for("cliente.ventas_listar"))


@cliente_bp.route("/empleados")
@login_required
@admin_empresa_requerido
def empleados_listar():
    empresa_id = _espectiva_empresa()
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
    empresa_id = _espectiva_empresa()

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
    empresa_id = _espectiva_empresa()
    empleado = Usuario.query.filter_by(id=empleado_id, empresa_id=empresa_id, rol=ROL_EMPLEADO).first_or_404()
    empleado.activo = not empleado.activo
    db.session.commit()
    flash(f"El empleado '{empleado.nombre}' ahora está {'activo' if empleado.activo else 'inactivo'}.", "info")
    return redirect(url_for("cliente.empleados_listar"))


@cliente_bp.route("/empleados/<int:empleado_id>/eliminar", methods=["POST"])
@login_required
@admin_empresa_requerido
def empleados_eliminar(empleado_id):
    empresa_id = _espectiva_empresa()
    empleado = Usuario.query.filter_by(id=empleado_id, empresa_id=empresa_id, rol=ROL_EMPLEADO).first_or_404()
    nombre = empleado.nombre
    db.session.delete(empleado)
    db.session.commit()
    flash(f"Empleado '{nombre}' eliminado.", "info")
    return redirect(url_for("cliente.empleados_listar"))