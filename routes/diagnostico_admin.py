from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Dimension, Indicador, Recomendacion
from routes.decoradores import superadmin_requerido

diagnostico_admin_bp = Blueprint("diagnostico_admin", __name__, url_prefix="/superadmin/diagnostico")


@diagnostico_admin_bp.route("/")
@login_required
@superadmin_requerido
def panel():
    dimensiones = Dimension.query.order_by(Dimension.nombre.asc()).all()
    total_indicadores = Indicador.query.count()
    total_recomendaciones = Recomendacion.query.count()
    return render_template(
        "superadmin/diagnostico/panel.html",
        dimensiones=dimensiones,
        total_indicadores=total_indicadores,
        total_recomendaciones=total_recomendaciones,
    )


@diagnostico_admin_bp.route("/dimensiones/nueva", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def dimension_nueva():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip() or None
        peso = request.form.get("peso", "1.0").strip()

        if not nombre:
            flash("El nombre de la dimensión es obligatorio.", "error")
            return render_template("superadmin/diagnostico/dimension_form.html", dimension=None)

        try:
            peso = float(peso)
        except ValueError:
            peso = 1.0

        if Dimension.query.filter_by(nombre=nombre).first():
            flash("Ya existe una dimensión con ese nombre.", "error")
            return render_template("superadmin/diagnostico/dimension_form.html", dimension=None)

        dim = Dimension(nombre=nombre, descripcion=descripcion, peso=peso)
        db.session.add(dim)
        db.session.commit()

        flash(f"Dimensión '{nombre}' creada correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    return render_template("superadmin/diagnostico/dimension_form.html", dimension=None)


@diagnostico_admin_bp.route("/dimensiones/<int:dim_id>/editar", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def dimension_editar(dim_id):
    dim = Dimension.query.get_or_404(dim_id)

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip() or None
        peso = request.form.get("peso", "1.0").strip()

        if not nombre:
            flash("El nombre de la dimensión es obligatorio.", "error")
            return render_template("superadmin/diagnostico/dimension_form.html", dimension=dim)

        try:
            peso = float(peso)
        except ValueError:
            peso = 1.0

        duplicado = Dimension.query.filter(Dimension.nombre == nombre, Dimension.id != dim.id).first()
        if duplicado:
            flash("Ya existe otra dimensión con ese nombre.", "error")
            return render_template("superadmin/diagnostico/dimension_form.html", dimension=dim)

        dim.nombre = nombre
        dim.descripcion = descripcion
        dim.peso = peso
        db.session.commit()

        flash(f"Dimensión '{nombre}' actualizada correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    return render_template("superadmin/diagnostico/dimension_form.html", dimension=dim)


@diagnostico_admin_bp.route("/dimensiones/<int:dim_id>/eliminar", methods=["POST"])
@login_required
@superadmin_requerido
def dimension_eliminar(dim_id):
    dim = Dimension.query.get_or_404(dim_id)
    nombre = dim.nombre
    db.session.delete(dim)
    db.session.commit()
    flash(f"Dimensión '{nombre}' eliminada.", "info")
    return redirect(url_for("diagnostico_admin.panel"))


@diagnostico_admin_bp.route("/indicadores/nuevo", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def indicador_nuevo():
    dimensiones = Dimension.query.order_by(Dimension.nombre.asc()).all()

    if request.method == "POST":
        dimension_id = request.form.get("dimension_id", type=int)
        texto = request.form.get("texto", "").strip()
        peso = request.form.get("peso", "1.0").strip()
        tipo_medicion = request.form.get("tipo_medicion", "AUTOREPORTADO").strip()

        errores = []
        if not texto:
            errores.append("El texto de la pregunta es obligatorio.")
        if not dimension_id:
            errores.append("Debes seleccionar una dimensión.")
        if tipo_medicion not in ("AUTOREPORTADO", "CALCULADO"):
            errores.append("Tipo de medición no válido.")

        if errores:
            for e in errores:
                flash(e, "error")
            return render_template("superadmin/diagnostico/indicador_form.html", indicador=None, dimensiones=dimensiones)

        try:
            peso = float(peso)
        except ValueError:
            peso = 1.0

        ind = Indicador(
            dimension_id=dimension_id,
            texto=texto,
            peso=peso,
            tipo_medicion=tipo_medicion,
        )
        db.session.add(ind)
        db.session.commit()

        flash("Indicador creado correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    return render_template("superadmin/diagnostico/indicador_form.html", indicador=None, dimensiones=dimensiones)


@diagnostico_admin_bp.route("/indicadores/<int:ind_id>/editar", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def indicador_editar(ind_id):
    ind = Indicador.query.get_or_404(ind_id)
    dimensiones = Dimension.query.order_by(Dimension.nombre.asc()).all()

    if request.method == "POST":
        ind.dimension_id = request.form.get("dimension_id", type=int)
        ind.texto = request.form.get("texto", "").strip()
        ind.tipo_medicion = request.form.get("tipo_medicion", "AUTOREPORTADO").strip()

        try:
            ind.peso = float(request.form.get("peso", "1.0").strip())
        except ValueError:
            ind.peso = 1.0

        db.session.commit()
        flash("Indicador actualizado correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    return render_template("superadmin/diagnostico/indicador_form.html", indicador=ind, dimensiones=dimensiones)


@diagnostico_admin_bp.route("/indicadores/<int:ind_id>/eliminar", methods=["POST"])
@login_required
@superadmin_requerido
def indicador_eliminar(ind_id):
    ind = Indicador.query.get_or_404(ind_id)
    db.session.delete(ind)
    db.session.commit()
    flash("Indicador eliminado.", "info")
    return redirect(url_for("diagnostico_admin.panel"))


@diagnostico_admin_bp.route("/recomendaciones/nueva", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def recomendacion_nueva():
    dimensiones = Dimension.query.order_by(Dimension.nombre.asc()).all()

    if request.method == "POST":
        dimension_id = request.form.get("dimension_id", type=int)
        rango_min = request.form.get("rango_min", "0").strip()
        rango_max = request.form.get("rango_max", "100").strip()
        texto = request.form.get("texto", "").strip()
        prioridad = request.form.get("prioridad", "MEDIA").strip()

        errores = []
        if not texto:
            errores.append("El texto de la recomendación es obligatorio.")
        if not dimension_id:
            errores.append("Debes seleccionar una dimensión.")

        if errores:
            for e in errores:
                flash(e, "error")
            return render_template("superadmin/diagnostico/recomendacion_form.html", recomendacion=None, dimensiones=dimensiones)

        try:
            rango_min = float(rango_min)
            rango_max = float(rango_max)
        except ValueError:
            rango_min, rango_max = 0, 100

        rec = Recomendacion(
            dimension_id=dimension_id,
            rango_min=rango_min,
            rango_max=rango_max,
            texto=texto,
            prioridad=prioridad,
        )
        db.session.add(rec)
        db.session.commit()

        flash("Recomendación creada correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    return render_template("superadmin/diagnostico/recomendacion_form.html", recomendacion=None, dimensiones=dimensiones)


@diagnostico_admin_bp.route("/recomendaciones/<int:rec_id>/editar", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def recomendacion_editar(rec_id):
    rec = Recomendacion.query.get_or_404(rec_id)
    dimensiones = Dimension.query.order_by(Dimension.nombre.asc()).all()

    if request.method == "POST":
        rec.dimension_id = request.form.get("dimension_id", type=int)
        rec.texto = request.form.get("texto", "").strip()
        rec.prioridad = request.form.get("prioridad", "MEDIA").strip()

        try:
            rec.rango_min = float(request.form.get("rango_min", "0").strip())
            rec.rango_max = float(request.form.get("rango_max", "100").strip())
        except ValueError:
            pass

        db.session.commit()
        flash("Recomendación actualizada correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    return render_template("superadmin/diagnostico/recomendacion_form.html", recomendacion=rec, dimensiones=dimensiones)


@diagnostico_admin_bp.route("/recomendaciones/<int:rec_id>/eliminar", methods=["POST"])
@login_required
@superadmin_requerido
def recomendacion_eliminar(rec_id):
    rec = Recomendacion.query.get_or_404(rec_id)
    db.session.delete(rec)
    db.session.commit()
    flash("Recomendación eliminada.", "info")
    return redirect(url_for("diagnostico_admin.panel"))
