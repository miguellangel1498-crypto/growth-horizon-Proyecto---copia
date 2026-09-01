from flask import Flask, render_template

from config import Config
from extensions import bcrypt, db, login_manager
from services.auditoria import AutoAuditoria


def _migrar_esquema():
    from sqlalchemy import text

    insp = db.inspect(db.engine)

    if "usuarios" in insp.get_table_names():
        columnas_usuario = [c["name"] for c in insp.get_columns("usuarios")]
        if "cargo" not in columnas_usuario:
            db.session.execute(text("ALTER TABLE usuarios ADD COLUMN cargo VARCHAR(80)"))
        if "intentos_fallidos" not in columnas_usuario:
            db.session.execute(text("ALTER TABLE usuarios ADD COLUMN intentos_fallidos INTEGER NOT NULL DEFAULT 0"))
        if "ultimo_intento_fallido" not in columnas_usuario:
            db.session.execute(text("ALTER TABLE usuarios ADD COLUMN ultimo_intento_fallido DATETIME"))
        db.session.execute(text("UPDATE usuarios SET rol='superadmin' WHERE rol='admin'"))
        db.session.execute(text("UPDATE usuarios SET rol='empresa' WHERE rol='cliente'"))

    if "empresas" in insp.get_table_names():
        columnas_empresa = [c["name"] for c in insp.get_columns("empresas")]
        if "notas_admin" not in columnas_empresa:
            db.session.execute(text("ALTER TABLE empresas ADD COLUMN notas_admin TEXT"))

    db.session.commit()


def crear_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from models import Auditoria, Empresa, Sector, Usuario

    @login_manager.user_loader
    def cargar_usuario(usuario_id):
        return db.session.get(Usuario, int(usuario_id))

    @app.template_filter("moneda")
    def formato_moneda(valor):
        if valor is None:
            return "—"
        try:
            v = float(valor)
        except (TypeError, ValueError):
            return valor
        texto = f"{v:,.2f}"
        texto = texto.replace(",", "@").replace(".", ",").replace("@", ".")
        return f"$ {texto} COP"

    @app.context_processor
    def contexto_global():
        from models.roles import ESTADO_EMPRESA_PENDIENTE

        return {
            "cantidad_sectores": db.session.query(Sector).count(),
            "cantidad_empresas": db.session.query(Empresa).count(),
            "empresas_pendientes": db.session.query(Empresa).filter(Empresa.estado == ESTADO_EMPRESA_PENDIENTE).count(),
            "sectores": db.session.query(Sector).order_by(Sector.nombre.asc()).all(),
        }

    @app.errorhandler(403)
    def sin_permiso(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def no_encontrado(e):
        return render_template("404.html"), 404

    from routes.analisis import analisis_bp
    from routes.auth import auth_bp
    from routes.cliente import cliente_bp
    from routes.empresas import empresas_bp
    from routes.main import main_bp
    from routes.seguridad import seguridad_bp
    from routes.sectores import sectores_bp
    from routes.superadmin import superadmin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(empresas_bp)
    app.register_blueprint(sectores_bp)
    app.register_blueprint(seguridad_bp)
    app.register_blueprint(cliente_bp)
    app.register_blueprint(analisis_bp)
    app.register_blueprint(superadmin_bp)

    # ── Headers anti-caché para rutas protegidas ──────────────
    @app.after_request
    def _no_cache_protected(response):
        from flask_login import current_user

        if current_user.is_authenticated:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    AutoAuditoria.configurar()

    with app.app_context():
        db.create_all()
        _migrar_esquema()

        @app.cli.command("init-db")
        def init_db():
            db.create_all()
            print("Base de datos inicializada correctamente.")

    @app.cli.command("seed")
    def seed():
        from models import Configuracion, HorarioAtencion, Producto, Venta
        from models.roles import (
            ESTADO_EMPRESA_ACTIVO,
            ROL_EMPRESA,
            ROL_SUPERADMIN,
        )

        db.create_all()

        if Configuracion.obtener("registro_empresas_abierto") is None:
            Configuracion.poner("registro_empresas_abierto", "on",
                                "Permite que nuevas empresas se registren por su cuenta en la plataforma.")
            Configuracion.poner("requiere_aprobacion_empresa", "on",
                                "Las empresas que se registran quedan pendientes de aprobación del superadministrador.")
            Configuracion.poner("permitir_registro_personas", "on",
                                "Permite que usuarios particulares (analistas) se registren.")
            db.session.commit()
            print("Configuración global de permisos creada.")

        if Sector.query.count() == 0:
            db.session.add_all(
                [
                    Sector(nombre="Tecnología", descripcion="Software, hardware y servicios digitales", color="#0ea5e9"),
                    Sector(nombre="Manufactura", descripcion="Producción industrial y transformación", color="#10b981"),
                    Sector(nombre="Comercio", descripcion="Venta de bienes y servicios", color="#8b5cf6"),
                    Sector(nombre="Agroindustria", descripcion="Producción agrícola y procesamiento", color="#f59e0b"),
                    Sector(nombre="Financiero", descripcion="Banca, seguros y fintech", color="#ef4444"),
                ]
            )
            db.session.commit()
            print("Sectores creados.")

        if Usuario.query.count() == 0:
            admin = Usuario(nombre="Superadministrador", email="admin@growthhorizon.com", rol=ROL_SUPERADMIN)
            admin.set_password("Admin123!")
            db.session.add(admin)
            db.session.commit()
            print("Superadministrador creado: admin@growthhorizon.com / Admin123!")

            if Empresa.query.count() == 0:
                tecnologia = Sector.query.filter_by(nombre="Tecnología").first()
                db.session.add_all(
                    [
                        Empresa(nombre="Innovatech Solutions", ruc="20100011112", sector=tecnologia,
                                actividad="Desarrollo de software a medida", estado="activo"),
                        Empresa(nombre="NubeAndina S.A.C.", ruc="20100022223", sector=tecnologia,
                                actividad="Servicios de infraestructura cloud", estado="activo"),
                    ]
                )
                db.session.commit()
                print("Empresas de ejemplo creadas.")

            from datetime import datetime, timedelta

            empresa_demo = Empresa.query.filter_by(ruc="20555500001").first()
            if empresa_demo is None:
                comercio = Sector.query.filter_by(nombre="Comercio").first()
                empresa_demo = Empresa(
                    nombre="Café Horizonte S.A.C.",
                    ruc="20555500001",
                    sector=comercio,
                    actividad="Cafetería y productos gourmet",
                    estado="activo",
                )
                db.session.add(empresa_demo)
                db.session.commit()

        cliente = Usuario.query.filter_by(email="cliente@growthhorizon.com").first()
        if cliente is None:
            cliente = Usuario(nombre="María López", email="cliente@growthhorizon.com", rol=ROL_EMPRESA, empresa=empresa_demo)
            cliente.set_password("Cliente123!")
            db.session.add(cliente)
            db.session.commit()
            print("Administrador de empresa creado: cliente@growthhorizon.com / Cliente123!")

        if Producto.query.filter_by(empresa_id=empresa_demo.id).count() > 0:
            print("Datos demo de la empresa ya cargados.")
        else:
            datos_productos = [
                ("Café especial 500g", "Bebidas", 24.50),
                ("Café latte", "Bebidas", 12.00),
                ("Sándwich gourmet", "Alimentos", 18.90),
                ("Cheesecake", "Postres", 15.50),
                ("Jugo natural 1L", "Bebidas", 16.00),
                ("Té de hierbas", "Bebidas", 8.50),
            ]
            for nombre, categoria, precio in datos_productos:
                db.session.add(Producto(empresa_id=empresa_demo.id, nombre=nombre, categoria=categoria, precio=precio))
            db.session.commit()

            dias = [("Lunes", 0), ("Martes", 1), ("Miércoles", 2), ("Jueves", 3), ("Viernes", 4), ("Sábado", 5)]
            for nombre, numero in dias[:5]:
                db.session.add(HorarioAtencion(empresa_id=empresa_demo.id, dia=nombre, dia_numero=numero, apertura="08:00", cierre="17:00"))
            db.session.add(HorarioAtencion(empresa_id=empresa_demo.id, dia="Sábado", dia_numero=5, apertura="09:00", cierre="13:00"))
            db.session.commit()

            productos = Producto.query.filter_by(empresa_id=empresa_demo.id).all()
            import random

            base = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            ventas = []
            for i in range(35):
                producto = random.choice(productos)
                cantidad = random.randint(1, 4)
                hora = random.randint(7, 19)
                dia = random.randint(0, 5)
                momento = base - timedelta(days=dia, hours=(24 - hora))
                ventas.append(Venta(empresa_id=empresa_demo.id, producto_id=producto.id,
                                    cantidad=cantidad, precio_unitario=producto.precio, fecha=momento))
            db.session.add_all(ventas)
            db.session.commit()
            print("Café Horizonte listo con productos, horarios y 35 ventas demo.")

        print("Datos semilla listos.")

    return app


app = crear_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)