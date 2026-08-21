from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from extensions import db
from models import Sector
from routes.decoradores import admin_requerido

sectores_bp = Blueprint("sectores", __name__, url_prefix="/sectores")


@sectores_bp.route("/")
@login_required
@admin_requerido
def listar():
    sectores = Sector.query.order_by(Sector.nombre.asc()).all()
    return render_template("sectores/listar.html", sectores=sectores)


@sectores_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@admin_requerido
def nuevo():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip() or None
        color = request.form.get("color", "#0891b2")

        if not nombre:
            flash("El nombre del sector es obligatorio.", "error")
            return render_template("sectores/form.html", sector=None)

        if Sector.query.filter_by(nombre=nombre).first():
            flash("Ya existe un sector con ese nombre.", "error")
            return render_template("sectores/form.html", sector=None)

        sector = Sector(nombre=nombre, descripcion=descripcion, color=color)
        db.session.add(sector)
        db.session.commit()

        flash(f"Sector '{sector.nombre}' creado correctamente.", "success")
        return redirect(url_for("sectores.listar"))

    return render_template("sectores/form.html", sector=None)


@sectores_bp.route("/<int:sector_id>/editar", methods=["GET", "POST"])
@login_required
@admin_requerido
def editar(sector_id):
    sector = Sector.query.get_or_404(sector_id)

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()

        if not nombre:
            flash("El nombre del sector es obligatorio.", "error")
            return render_template("sectores/form.html", sector=sector)

        duplicado = Sector.query.filter(Sector.nombre == nombre, Sector.id != sector.id).first()
        if duplicado:
            flash("Ya existe un sector con ese nombre.", "error")
            return render_template("sectores/form.html", sector=sector)

        sector.nombre = nombre
        sector.descripcion = request.form.get("descripcion", "").strip() or None
        sector.color = request.form.get("color", "#0891b2")

        db.session.commit()
        flash(f"Sector '{sector.nombre}' actualizado correctamente.", "success")
        return redirect(url_for("sectores.listar"))

    return render_template("sectores/form.html", sector=sector)


@sectores_bp.route("/<int:sector_id>/eliminar", methods=["POST"])
@login_required
@admin_requerido
def eliminar(sector_id):
    sector = Sector.query.get_or_404(sector_id)
    nombre = sector.nombre

    if sector.empresas.count() > 0:
        flash(f"No se puede eliminar el sector '{nombre}' porque tiene empresas asociadas.", "error")
        return redirect(url_for("sectores.listar"))

    db.session.delete(sector)
    db.session.commit()
    flash(f"Sector '{nombre}' eliminado.", "info")
    return redirect(url_for("sectores.listar"))