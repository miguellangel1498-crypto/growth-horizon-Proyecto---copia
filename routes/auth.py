from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from extensions import db
from models import Usuario
from services.auditoria import registrar_login, registrar_y_commit

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        recuerdame = request.form.get("recordarme") == "on"

        usuario = Usuario.query.filter(db.func.lower(Usuario.email) == email).first()

        if usuario is None:
            registrar_login(Usuario(email=email, rol="anonimo"), exitoso=False, motivo="Email no registrado")
            flash("Credenciales inválidas.", "error")
            return render_template("auth/login.html"), 401

        if not usuario.check_password(password):
            registrar_login(usuario, exitoso=False, motivo="Contraseña incorrecta")
            flash("Credenciales inválidas.", "error")
            return render_template("auth/login.html"), 401

        if not usuario.activo:
            registrar_login(usuario, exitoso=False, motivo="Cuenta inactiva")
            flash("Tu cuenta está inactiva. Contacta al administrador.", "error")
            return render_template("auth/login.html"), 403

        login_user(usuario, remember=recuerdame)
        usuario.ultimo_acceso = datetime.utcnow()
        db.session.commit()
        registrar_y_commit("LOGIN_EXITOSO", entidad="Usuario", entidad_id=usuario.id,
                           detalle=f"Ingreso de {usuario.email}")

        flash(f"Bienvenido/a de nuevo, {usuario.nombre.capitalize()}!", "success")
        siguiente = request.args.get("next")
        if siguiente and siguiente.startswith("/"):
            return redirect(siguiente)
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirmar = request.form.get("confirmar_password", "")

        errores = []
        if not nombre or not email or not password:
            errores.append("Todos los campos son obligatorios.")
        if len(password) < 8:
            errores.append("La contraseña debe tener al menos 8 caracteres.")
        if password != confirmar:
            errores.append("Las contraseñas no coinciden.")
        if Usuario.query.filter_by(email=email).first():
            errores.append("Ya existe una cuenta con ese correo.")

        if errores:
            for e in errores:
                flash(e, "error")
            return render_template("auth/registro.html")

        es_primero = Usuario.query.count() == 0
        usuario = Usuario(nombre=nombre, email=email, rol="admin" if es_primero else "analista")
        usuario.set_password(password)
        db.session.add(usuario)
        db.session.commit()

        registrar_y_commit(
            "REGISTRO_USUARIO",
            entidad="Usuario",
            entidad_id=usuario.id,
            detalle=f"Nuevo usuario {email} con rol {usuario.rol}",
        )

        login_user(usuario)
        usuario.ultimo_acceso = datetime.utcnow()
        db.session.commit()

        flash(f"Bienvenido/a, {usuario.nombre.capitalize()}! Cuenta creada correctamente.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/registro.html")


@auth_bp.route("/salir")
def logout():
    if current_user.is_authenticated:
        registrar_y_commit("LOGOUT", entidad="Usuario", entidad_id=current_user.id,
                           detalle=f"Cierre de sesión de {current_user.email}")
    logout_user()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for("main.index"))