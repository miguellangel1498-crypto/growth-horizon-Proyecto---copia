from datetime import datetime, date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Producto, Venta
from routes.decoradores import empleado_requerido

empleado_bp = Blueprint("empleado", __name__, url_prefix="/empleado")


def _empresa_id():
    """Retorna el ID de la empresa del empleado actual."""
    return current_user.empresa.id


@empleado_bp.route("/")
@login_required
@empleado_requerido
def panel():
    """Panel principal del empleado: acciones rapidas y resumen del dia."""
    empresa_id = _empresa_id()
    empresa = current_user.empresa

    # Ventas registradas HOY en la empresa
    hoy = date.today()
    ventas_hoy = (
        Venta.query
        .filter(
            Venta.empresa_id == empresa_id,
            db.func.date(Venta.fecha) == hoy,
        )
        .order_by(Venta.fecha.desc())
        .all()
    )
    total_ventas_hoy = len(ventas_hoy)

    # Total de productos disponibles para vender
    total_productos = Producto.query.filter_by(empresa_id=empresa_id).count()

    return render_template(
        "empleado/panel.html",
        empresa=empresa,
        ventas_hoy=ventas_hoy,
        total_ventas_hoy=total_ventas_hoy,
        total_productos=total_productos,
        hoy=hoy,
    )


@empleado_bp.route("/productos")
@login_required
@empleado_requerido
def productos():
    """Lista de productos con precios: solo lectura. El empleado puede consultar y buscar."""
    empresa_id = _empresa_id()
    busqueda = request.args.get("q", "").strip()

    consulta = Producto.query.filter_by(empresa_id=empresa_id)
    if busqueda:
        consulta = consulta.filter(
            db.or_(
                Producto.nombre.ilike(f"%{busqueda}%"),
                Producto.categoria.ilike(f"%{busqueda}%"),
            )
        )

    productos = consulta.order_by(Producto.nombre.asc()).all()
    return render_template(
        "empleado/productos.html",
        productos=productos,
        busqueda=busqueda,
        empresa=current_user.empresa,
    )


@empleado_bp.route("/ventas")
@login_required
@empleado_requerido
def ventas():
    """Historial de ventas del dia actual (toda la empresa). Sin totales financieros."""
    empresa_id = _empresa_id()
    hoy = date.today()

    ventas = (
        Venta.query
        .filter(
            Venta.empresa_id == empresa_id,
            db.func.date(Venta.fecha) == hoy,
        )
        .order_by(Venta.fecha.desc())
        .all()
    )

    return render_template(
        "empleado/ventas.html",
        ventas=ventas,
        hoy=hoy,
        empresa=current_user.empresa,
    )


@empleado_bp.route("/ventas/nueva", methods=["GET", "POST"])
@login_required
@empleado_requerido
def ventas_nueva():
    """Registrar una nueva venta. El empleado selecciona producto y cantidad."""
    empresa_id = _empresa_id()
    productos = Producto.query.filter_by(empresa_id=empresa_id).order_by(Producto.nombre.asc()).all()

    if request.method == "POST":
        producto_id = request.form.get("producto_id", type=int)
        cantidad_str = request.form.get("cantidad", "1").strip()

        producto = (
            Producto.query.filter_by(id=producto_id, empresa_id=empresa_id).first()
            if producto_id
            else None
        )

        if producto is None:
            flash("Selecciona un producto valido de la lista.", "error")
            return render_template(
                "empleado/ventas_nueva.html",
                productos=productos,
                empresa=current_user.empresa,
            )

        try:
            cantidad = max(int(cantidad_str), 1)
        except ValueError:
            cantidad = 1

        venta = Venta(
            empresa_id=empresa_id,
            producto_id=producto.id,
            cantidad=cantidad,
            precio_unitario=producto.precio,
            fecha=datetime.utcnow(),
        )
        db.session.add(venta)
        db.session.commit()

        flash(
            f"Venta registrada: {cantidad}x {producto.nombre}",
            "success",
        )
        return redirect(url_for("empleado.ventas"))

    return render_template(
        "empleado/ventas_nueva.html",
        productos=productos,
        empresa=current_user.empresa,
    )
