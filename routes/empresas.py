from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Empresa, HorarioAtencion, Producto, Sector, Venta
from routes.decoradores import admin_requerido
from services.exporter import exportar_inventario, exportar_ventas

empresas_bp = Blueprint("empresas", __name__, url_prefix="/empresas")


@empresas_bp.route("/")
@login_required
@admin_requerido
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
@admin_requerido
def detalle(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    productos = Producto.query.filter_by(empresa_id=empresa.id).order_by(Producto.nombre.asc()).all()
    horarios = HorarioAtencion.query.filter_by(empresa_id=empresa.id).order_by(HorarioAtencion.dia_numero.asc()).all()
    ventas = Venta.query.filter_by(empresa_id=empresa.id).order_by(Venta.fecha.desc()).limit(12).all()

    total_ingresos = db.session.query(db.func.sum(Venta.precio_unitario * Venta.cantidad)).filter(
        Venta.empresa_id == empresa.id
    ).scalar() or 0
    total_ventas = Venta.query.filter_by(empresa_id=empresa.id).count()
    total_productos = Producto.query.filter_by(empresa_id=empresa.id).count()
    usuarios = [u for u in empresa.usuarios if u.activo]

    return render_template(
        "empresas/detalle.html",
        empresa=empresa,
        productos=productos,
        horarios=horarios,
        ventas=ventas,
        total_ingresos=total_ingresos,
        total_ventas=total_ventas,
        total_productos=total_productos,
        usuarios=usuarios,
    )


@empresas_bp.route("/exportar/ventas")
@login_required
@admin_requerido
def exportar_ventas_xlsx():
    ventas = Venta.query.order_by(Venta.fecha.desc()).all()
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
        download_name="reporte_ventas_todas.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@empresas_bp.route("/exportar/inventario")
@login_required
@admin_requerido
def exportar_inventario_xlsx():
    productos = Producto.query.order_by(Producto.nombre.asc()).all()
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
        download_name="reporte_inventario_todas.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@empresas_bp.route("/<int:empresa_id>/exportar/ventas")
@login_required
@admin_requerido
def exportar_ventas_empresa_xlsx(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    ventas = Venta.query.filter_by(empresa_id=empresa.id).order_by(Venta.fecha.desc()).all()
    filas = [
        (
            venta.id,
            empresa.nombre,
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
        download_name=f"ventas_{empresa.nombre.replace(' ', '_')}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@empresas_bp.route("/<int:empresa_id>/exportar/inventario")
@login_required
@admin_requerido
def exportar_inventario_empresa_xlsx(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    productos = Producto.query.filter_by(empresa_id=empresa.id).order_by(Producto.nombre.asc()).all()
    filas = []
    for producto in productos:
        unidades = db.session.query(db.func.sum(Venta.cantidad)).filter(Venta.producto_id == producto.id).scalar() or 0
        ingresos = db.session.query(db.func.sum(Venta.precio_unitario * Venta.cantidad)).filter(
            Venta.producto_id == producto.id
        ).scalar() or 0
        filas.append(
            (
                producto.id,
                empresa.nombre,
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
        download_name=f"inventario_{empresa.nombre.replace(' ', '_')}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@empresas_bp.route("/nueva", methods=["GET", "POST"])
@login_required
@admin_requerido
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
        )
        db.session.add(empresa)
        db.session.commit()

        flash(f"Empresa '{empresa.nombre}' creada correctamente.", "success")
        return redirect(url_for("empresas.listar"))

    return render_template("empresas/form.html", sectores=sectores, empresa=None)


@empresas_bp.route("/<int:empresa_id>/editar", methods=["GET", "POST"])
@login_required
@admin_requerido
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

        db.session.commit()
        flash(f"Empresa '{empresa.nombre}' actualizada correctamente.", "success")
        return redirect(url_for("empresas.listar"))

    return render_template("empresas/form.html", sectores=sectores, empresa=empresa)


@empresas_bp.route("/<int:empresa_id>/eliminar", methods=["POST"])
@login_required
@admin_requerido
def eliminar(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    nombre = empresa.nombre
    db.session.delete(empresa)
    db.session.commit()
    flash(f"Empresa '{nombre}' eliminada.", "info")
    return redirect(url_for("empresas.listar"))