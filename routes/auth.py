from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from extensions import db
from models import Empresa, Sector, Usuario
from models.roles import ROL_ANALISTA, ROL_EMPRESA, ROL_SUPERADMIN, ESTADO_EMPRESA_PENDIENTE
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

        if usuario.empresa is not None and not usuario.acceso_empresa_activa:
            registrar_login(usuario, exitoso=False, motivo=f"Empresa {usuario.empresa.estado}")
            if usuario.empresa.esta_pendiente:
                flash("Tu empresa está pendiente de aprobación por el superadministrador. Te avisaremos cuando sea activada.", "warning")
            elif usuario.empresa.esta_rechazada:
                flash("El acceso de tu empresa fue rechazado. Contacta al superadministrador para más información.", "error")
            else:
                flash("El acceso de tu empresa está suspendido. Contacta al superadministrador.", "error")
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
        tipo_cuenta = request.form.get("tipo_cuenta", "persona")
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirmar = request.form.get("confirmar_password", "")

        from models import Configuracion

        if tipo_cuenta == "empresa" and not Configuracion.boolean("registro_empresas_abierto", True):
            flash("El registro de empresas está deshabilitado temporalmente.", "error")
            return redirect(url_for("auth.registro"))
        if tipo_cuenta == "persona" and not Configuracion.boolean("permitir_registro_personas", True):
            flash("El registro de usuarios particulares está deshabilitado temporalmente.", "error")
            return redirect(url_for("auth.registro"))

        errores = []
        if not nombre or not email or not password:
            errores.append("Todos los campos son obligatorios.")
        if len(password) < 8:
            errores.append("La contraseña debe tener al menos 8 caracteres.")
        if password != confirmar:
            errores.append("Las contraseñas no coinciden.")
        if Usuario.query.filter_by(email=email).first():
            errores.append("Ya existe una cuenta con ese correo.")

        razon_social = None
        ruc = None
        sector_id = None
        actividad = None
        correo_empresa = None
        telefono = None
        direccion = None
        sitio_web = None
        if tipo_cuenta == "empresa":
            razon_social = request.form.get("razon_social", "").strip()
            ruc = request.form.get("ruc", "").strip() or None
            sector_id = request.form.get("sector_id", type=int) or None
            actividad = request.form.get("actividad", "").strip() or None
            correo_empresa = request.form.get("correo_empresa", "").strip() or None
            telefono = request.form.get("telefono", "").strip() or None
            direccion = request.form.get("direccion", "").strip() or None
            sitio_web = request.form.get("sitio_web", "").strip() or None
            if not razon_social:
                errores.append("El nombre de la empresa es obligatorio.")
            if not actividad:
                errores.append("Describe la actividad de tu negocio.")
            if not telefono:
                errores.append("El teléfono de contacto es obligatorio.")
            if ruc and Empresa.query.filter_by(ruc=ruc).first():
                errores.append("Ya existe una empresa con ese RUC.")

        if errores:
            for e in errores:
                flash(e, "error")
            sectores = Sector.query.order_by(Sector.nombre.asc()).all()
            return render_template(
                "auth/registro.html",
                sectores=sectores,
                tipo_cuenta=tipo_cuenta,
                datos_empresa={
                    "razon_social": razon_social,
                    "ruc": ruc,
                    "actividad": actividad,
                    "correo_empresa": correo_empresa,
                    "telefono": telefono,
                    "direccion": direccion,
                    "sitio_web": sitio_web,
                },
            )

        if tipo_cuenta == "empresa":
            empresa = Empresa(
                nombre=razon_social,
                ruc=ruc,
                sector_id=sector_id,
                actividad=actividad,
                correo=correo_empresa,
                telefono=telefono,
                direccion=direccion,
                sitio_web=sitio_web,
                estado=ESTADO_EMPRESA_PENDIENTE,
            )
            db.session.add(empresa)
            db.session.commit()

            usuario = Usuario(nombre=nombre, email=email, rol=ROL_EMPRESA, empresa=empresa)
            usuario.set_password(password)
            db.session.add(usuario)
            db.session.commit()

            registrar_y_commit(
                "REGISTRO_EMPRESA",
                entidad="Usuario",
                entidad_id=usuario.id,
                detalle=f"Nueva empresa {razon_social} ({email}) pendiente de aprobación",
            )

            login_user(usuario)
            usuario.ultimo_acceso = datetime.utcnow()
            db.session.commit()

            flash(
                "¡Gracias por registrar tu empresa! Tu solicitud está pendiente de aprobación por el "
                "superadministrador. Recibirás acceso una vez sea aprobada.",
                "info",
            )
            return redirect(url_for("main.index"))

        es_primero = Usuario.query.count() == 0
        usuario = Usuario(nombre=nombre, email=email, rol=ROL_SUPERADMIN if es_primero else ROL_ANALISTA)
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

    from models import Configuracion

    sectores = Sector.query.order_by(Sector.nombre.asc()).all()
    registro_empresas = Configuracion.boolean("registro_empresas_abierto", True)
    registro_personas = Configuracion.boolean("permitir_registro_personas", True)
    return render_template(
        "auth/registro.html",
        sectores=sectores,
        tipo_cuenta="persona",
        datos_empresa=None,
        registro_empresas=registro_empresas,
        registro_personas=registro_personas,
    )


@auth_bp.route("/salir")
def logout():
    if current_user.is_authenticated:
        registrar_y_commit("LOGOUT", entidad="Usuario", entidad_id=current_user.id,
                           detalle=f"Cierre de sesión de {current_user.email}")
    logout_user()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for("main.index"))