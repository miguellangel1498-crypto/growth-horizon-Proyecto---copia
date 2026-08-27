from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from extensions import db
from models import HorarioAtencion, Producto, Venta
from models.roles import ROL_EMPRESA, ROL_SUPERADMIN

analisis_bp = Blueprint("analisis", __name__, url_prefix="/analisis")


def _hora_label(hora):
    try:
        return f"{int(hora):02d}:00"
    except (TypeError, ValueError):
        return "-"


@analisis_bp.route("/")
@login_required
def principal():
    if current_user.rol not in (ROL_SUPERADMIN, ROL_EMPRESA):
        abort(403)

    empresa = current_user.empresa
    es_admin = current_user.rol == ROL_SUPERADMIN
    empresa_id = None if es_admin else (empresa.id if empresa else None)

    def cond_venta(*extra):
        if es_admin:
            return list(extra)
        return [Venta.empresa_id == empresa_id, *extra]

    def cond_producto(*extra):
        if es_admin:
            return list(extra)
        return [Producto.empresa_id == empresa_id, *extra]

    consulta_ventas = Venta.query.filter(*cond_venta())

    total_ingresos = db.session.query(db.func.sum(Venta.precio_unitario * Venta.cantidad)).filter(*cond_venta()).scalar() or 0
    total_unidades = db.session.query(db.func.sum(Venta.cantidad)).filter(*cond_venta()).scalar() or 0
    total_ventas = consulta_ventas.count()
    ticket_promedio = (total_ingresos / total_ventas) if total_ventas else 0
    productos_registrados = Producto.query.filter(*cond_producto()).count()

    productos_mas_vendidos = (
        db.session.query(
            Producto.nombre,
            Producto.categoria,
            db.func.sum(Venta.cantidad).label("unidades"),
            db.func.sum(Venta.precio_unitario * Venta.cantidad).label("ingresos"),
        )
        .join(Venta, Venta.producto_id == Producto.id)
        .filter(*cond_venta())
        .group_by(Producto.id, Producto.nombre, Producto.categoria)
        .order_by(db.func.sum(Venta.cantidad).desc())
        .limit(8)
        .all()
    )

    ingresos_por_categoria = (
        db.session.query(Producto.categoria, db.func.sum(Venta.precio_unitario * Venta.cantidad).label("ingresos"))
        .join(Venta, Venta.producto_id == Producto.id)
        .filter(*cond_venta(), Producto.categoria.isnot(None))
        .group_by(Producto.categoria)
        .order_by(db.func.sum(Venta.precio_unitario * Venta.cantidad).desc())
        .all()
    )

    movimiento_por_hora = (
        db.session.query(
            db.func.cast(db.func.strftime("%H", Venta.fecha), db.Integer).label("hora"),
            db.func.count(Venta.id).label("ventas"),
            db.func.sum(Venta.precio_unitario * Venta.cantidad).label("ingresos"),
        )
        .filter(*cond_venta())
        .group_by("hora")
        .order_by(db.func.count(Venta.id).desc())
        .all()
    )
    horas_top = [( _hora_label(hora), ventas, ingresos) for hora, ventas, ingresos in movimiento_por_hora[:6]]

    dias_top = (
        db.session.query(
            db.func.strftime("%w", Venta.fecha).label("dia"),
            db.func.count(Venta.id).label("ventas"),
            db.func.sum(Venta.precio_unitario * Venta.cantidad).label("ingresos"),
        )
        .filter(*cond_venta())
        .group_by("dia")
        .order_by(db.func.count(Venta.id).desc())
        .all()
    )
    nombres_dia = {0: "Domingo", 1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes", 6: "Sábado"}
    dias_top = [(nombres_dia.get(int(d), "Día"), ventas, ingresos) for d, ventas, ingresos in dias_top[:7]]

    ventas_por_dia = (
        db.session.query(db.func.date(Venta.fecha).label("fecha"), db.func.sum(Venta.precio_unitario * Venta.cantidad).label("ingresos"))
        .filter(*cond_venta())
        .group_by("fecha")
        .order_by("fecha")
        .limit(15)
        .all()
    )

    if es_admin:
        horarios = HorarioAtencion.query.order_by(HorarioAtencion.dia_numero.asc()).all()
    else:
        horarios = HorarioAtencion.query.filter_by(empresa_id=empresa_id).order_by(HorarioAtencion.dia_numero.asc()).all()

    producto_datos_hora = {hora: {"ventas": v, "ingresos": i} for hora, v, i in movimiento_por_hora}
    etiquetas_horas = [_hora_label(h) for h in range(7, 21)]
    productos_chart = {
        "labels": [nombre for nombre, _c, _u, _i in productos_mas_vendidos],
        "unidades": [int(u) for _n, _c, u, _i in productos_mas_vendidos],
        "ingresos": [float(i) for _n, _c, _u, i in productos_mas_vendidos],
    }
    horas_chart = {
        "labels": etiquetas_horas,
        "ventas": [producto_datos_hora.get(hora, {"ventas": 0})["ventas"] for hora in range(7, 21)],
        "ingresos": [producto_datos_hora.get(hora, {"ingresos": 0})["ingresos"] for hora in range(7, 21)],
    }

    return render_template(
        "analisis.html",
        empresa=empresa,
        es_admin=es_admin,
        total_ingresos=total_ingresos,
        total_unidades=total_unidades,
        total_ventas=total_ventas,
        ticket_promedio=ticket_promedio,
        productos_registrados=productos_registrados,
        productos_mas_vendidos=productos_mas_vendidos,
        ingresos_por_categoria=ingresos_por_categoria,
        horas_top=horas_top,
        dias_top=dias_top,
        ventas_por_dia=ventas_por_dia,
        horarios=horarios,
        productos_chart=productos_chart,
        horas_chart=horas_chart,
    )