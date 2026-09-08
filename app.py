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
        db.session.execute(text("UPDATE usuarios SET rol='empleado' WHERE rol='analista' AND empresa_id IS NOT NULL"))
        db.session.execute(text("UPDATE usuarios SET activo=0 WHERE rol='analista' AND empresa_id IS NULL"))
        db.session.execute(text("UPDATE usuarios SET rol='empleado' WHERE rol='analista'"))

    if "empresas" in insp.get_table_names():
        columnas_empresa = [c["name"] for c in insp.get_columns("empresas")]
        if "notas_admin" not in columnas_empresa:
            db.session.execute(text("ALTER TABLE empresas ADD COLUMN notas_admin TEXT"))
        if "tamano_empresa" not in columnas_empresa:
            db.session.execute(text("ALTER TABLE empresas ADD COLUMN tamano_empresa VARCHAR(20) NOT NULL DEFAULT 'PEQUENA'"))

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
    from routes.diagnostico import diagnostico_bp
    from routes.diagnostico_admin import diagnostico_admin_bp
    from routes.empleado import empleado_bp
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
    app.register_blueprint(empleado_bp)
    app.register_blueprint(analisis_bp)
    app.register_blueprint(superadmin_bp)
    app.register_blueprint(diagnostico_bp)
    app.register_blueprint(diagnostico_admin_bp)

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
        from models import Configuracion, Dimension, IndiceMadurez, Indicador, Recomendacion, RespuestaDiagnostico, Segmento
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
                                "Permite que usuarios particulares se registren.")
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

        if Dimension.query.count() == 0:
            dimensiones_datos = [
                ("Financiera", "Salud financiera, control de ingresos y gastos, planificación presupuestaria", 1.0),
                ("Operación", "Procesos internos, eficiencia operativa, control de inventario", 1.0),
                ("Clientes/Ventas", "Gestión de clientes, estrategia comercial, canales de venta", 1.0),
                ("Digitalización", "Uso de herramientas digitales, presencia online, transformación digital", 1.2),
                ("Datos", "Gestión de datos, toma de decisiones basada en datos", 1.0),
                ("Seguridad", "Protección de datos, ciberseguridad, respaldos", 0.8),
                ("Automatización", "Automatización de procesos, uso de tecnología para reducir tareas manuales", 1.0),
                ("Analítica", "Análisis de datos, métricas, reportes, inteligencia de negocio", 1.0),
            ]
            dims_creadas = {}
            for nombre, desc, peso in dimensiones_datos:
                d = Dimension(nombre=nombre, descripcion=desc, peso=peso)
                db.session.add(d)
                db.session.flush()
                dims_creadas[nombre] = d

            indicadores_datos = [
                ("Financiera", "¿Llevas un registro organizado de tus ingresos y gastos mensuales?", 1.0, "AUTOREPORTADO"),
                ("Financiera", "¿Cuál fue tu ingreso aproximado el último mes (en pesos)?", 1.0, "AUTOREPORTADO"),
                ("Financiera", "¿Cuentas con un presupuesto mensual definido?", 1.0, "AUTOREPORTADO"),
                ("Financiera", "Promedio de respuestas financieras AUTOREPORTADO", 0.5, "CALCULADO"),
                ("Operación", "¿Llevas un control organizado de tu inventario?", 1.0, "AUTOREPORTADO"),
                ("Operación", "¿Tus procesos principales están documentados o estandarizados?", 1.0, "AUTOREPORTADO"),
                ("Operación", "¿Qué porcentaje de tus ingresos proviene de canales digitales?", 1.0, "AUTOREPORTADO"),
                ("Operación", "Indicador de madurez operativa calculado", 0.5, "CALCULADO"),
                ("Clientes/Ventas", "¿Tienes una base de datos de tus clientes?", 1.0, "AUTOREPORTADO"),
                ("Clientes/Ventas", "¿Utilizas alguna herramienta para gestionar clientes (CRM)?", 1.0, "AUTOREPORTADO"),
                ("Clientes/Ventas", "¿Mides la satisfacción de tus clientes?", 1.0, "AUTOREPORTADO"),
                ("Digitalización", "¿Tu negocio tiene presencia online (página web, redes sociales)?", 1.2, "AUTOREPORTADO"),
                ("Digitalización", "¿Utilizas herramientas digitales para gestionar tu negocio?", 1.2, "AUTOREPORTADO"),
                ("Digitalización", "¿Vendes o promocionas tus productos/servicios por internet?", 1.0, "AUTOREPORTADO"),
                ("Datos", "¿Generas reportes periódicos de tu negocio?", 1.0, "AUTOREPORTADO"),
                ("Datos", "¿Tomas decisiones de negocio basadas en datos o estadísticas?", 1.0, "AUTOREPORTADO"),
                ("Datos", "Calidad de datos basada en completitud de respuestas", 0.5, "CALCULADO"),
                ("Seguridad", "¿Cuentas con respaldos (backups) de tu información?", 1.0, "AUTOREPORTADO"),
                ("Seguridad", "¿Tus empleados conocen buenas prácticas de seguridad digital?", 1.0, "AUTOREPORTADO"),
                ("Automatización", "¿Utilizas software para tareas repetitivas (contabilidad, inventario)?", 1.0, "AUTOREPORTADO"),
                ("Automatización", "¿Algunos de tus procesos se ejecutan automáticamente?", 1.0, "AUTOREPORTADO"),
                ("Analítica", "¿Revisas métricas o indicadores de tu negocio regularmente?", 1.0, "AUTOREPORTADO"),
                ("Analítica", "¿Utilizas herramientas de análisis (Excel avanzado, BI, dashboards)?", 1.0, "AUTOREPORTADO"),
                ("Analítica", "Tendencia de mejora basada en histórico de índices", 0.5, "CALCULADO"),
            ]

            for dim_nombre, texto, peso, tipo in indicadores_datos:
                dim = dims_creadas.get(dim_nombre)
                if dim:
                    ind = Indicador(dimension_id=dim.id, texto=texto, peso=peso, tipo_medicion=tipo)
                    db.session.add(ind)

            db.session.commit()
            print("Dimensiones e indicadores creados.")

        if Segmento.query.count() == 0:
            db.session.add_all([
                Segmento(nombre="Inicial", rango_min=0, rango_max=39,
                         descripcion="La empresa está en etapas tempranas de madurez digital. Procesos mayormente manuales, poca tecnología."),
                Segmento(nombre="En Desarrollo", rango_min=40, rango_max=69,
                         descripcion="La empresa ha iniciado su transformación digital con algunos procesos automatizados y herramientas implementadas."),
                Segmento(nombre="Consolidado", rango_min=70, rango_max=100,
                         descripcion="La empresa tiene alto nivel de madurez digital con procesos optimizados, datos integrados y analítica avanzada."),
            ])
            db.session.commit()
            print("Segmentos creados.")

        if Recomendacion.query.count() == 0:
            from models import Dimension as DimModel

            dims_recs = DimModel.query.all()
            dim_ids = {d.nombre: d.id for d in dims_recs}

            recomendaciones_datos = [
                ("Financiera", 0, 39, "Implementa un sistema básico de registro de ingresos y gastos. Usa una hoja de cálculo para empezar.", "ALTA"),
                ("Financiera", 40, 69, "Define un presupuesto mensual y compáralo con tus resultados reales cada mes.", "MEDIA"),
                ("Financiera", 70, 100, "Considera software contable avanzado y proyecciones financieras trimestrales.", "BAJA"),
                ("Operación", 0, 39, "Documenta tus procesos principales y crea un inventario básico de productos.", "ALTA"),
                ("Operación", 40, 69, "Implementa herramientas de gestión de inventario y estandariza tus flujos de trabajo.", "MEDIA"),
                ("Operación", 70, 100, "Automatiza procesos repetitivos e integra sistemas para eficiencia óptima.", "BAJA"),
                ("Clientes/Ventas", 0, 39, "Crea una lista de clientes con datos de contacto y empieza a registrar interacciones.", "ALTA"),
                ("Clientes/Ventas", 40, 69, "Implementa un CRM básico y mide satisfacción del cliente periódicamente.", "MEDIA"),
                ("Clientes/Ventas", 70, 100, "Usa segmentación avanzada de clientes y automatiza campañas de marketing.", "BAJA"),
                ("Digitalización", 0, 39, "Crea perfiles en redes sociales y considera una página web básica.", "ALTA"),
                ("Digitalización", 40, 69, "Integra herramientas digitales para gestión interna y presencia online.", "MEDIA"),
                ("Digitalización", 70, 100, "Optimiza tu ecosistema digital con omnicanalidad y transformación avanzada.", "BAJA"),
                ("Datos", 0, 39, "Empieza a registrar datos clave del negocio en hojas de cálculo.", "ALTA"),
                ("Datos", 40, 69, "Crea dashboards básicos y reportes mensuales con métricas importantes.", "MEDIA"),
                ("Datos", 70, 100, "Implementa analítica predictiva y toma de decisiones basada en datos.", "BAJA"),
                ("Seguridad", 0, 39, "Configura respaldos automáticos y crea contraseñas seguras.", "ALTA"),
                ("Seguridad", 40, 69, "Capacita a tu equipo en seguridad digital y implementa políticas básicas.", "MEDIA"),
                ("Seguridad", 70, 100, "Audita regularmente tu seguridad y cumple con normativas de protección de datos.", "BAJA"),
                ("Automatización", 0, 39, "Identifica tareas repetitivas que puedan automatizarse con herramientas simples.", "ALTA"),
                ("Automatización", 40, 69, "Implementa software especializado para automatizar procesos clave.", "MEDIA"),
                ("Automatización", 70, 100, "Integra sistemas y crea flujos de trabajo automatizados complejos.", "BAJA"),
                ("Analítica", 0, 39, "Define 3-5 métricas clave y revísalas semanalmente.", "ALTA"),
                ("Analítica", 40, 69, "Implementa herramientas de visualización y reportes automatizados.", "MEDIA"),
                ("Analítica", 70, 100, "Usa inteligencia de negocio y analítica predictiva para estrategia.", "BAJA"),
            ]

            for dim_nombre, r_min, r_max, texto, prioridad in recomendaciones_datos:
                dim_id = dim_ids.get(dim_nombre)
                if dim_id:
                    db.session.add(Recomendacion(
                        dimension_id=dim_id, rango_min=r_min, rango_max=r_max,
                        texto=texto, prioridad=prioridad,
                    ))

            db.session.commit()
            print("Recomendaciones creadas.")

        if Empresa.query.filter_by(ruc="20555500001").first() is None:
            comercio = Sector.query.filter_by(nombre="Comercio").first()
            tecnologia = Sector.query.filter_by(nombre="Tecnología").first()

            empresa_micro = Empresa(
                nombre="Café Horizonte S.A.C.",
                ruc="20555500001",
                sector=comercio,
                actividad="Cafetería y productos gourmet",
                estado="activo",
                tamano_empresa="MICRO",
            )
            empresa_mediana = Empresa(
                nombre="Innovatech Solutions",
                ruc="20100011112",
                sector=tecnologia,
                actividad="Desarrollo de software a medida",
                estado="activo",
                tamano_empresa="MEDIANA",
            )
            db.session.add_all([empresa_micro, empresa_mediana])
            db.session.commit()

            if Usuario.query.filter_by(email="admin@cafehorizonte.com").first() is None:
                admin_micro = Usuario(
                    nombre="María López",
                    email="admin@cafehorizonte.com",
                    rol=ROL_EMPRESA,
                    empresa=empresa_micro,
                )
                admin_micro.set_password("Cliente123!")
                db.session.add(admin_micro)

            if Usuario.query.filter_by(email="admin@innovatech.com").first() is None:
                admin_med = Usuario(
                    nombre="Carlos Ruiz",
                    email="admin@innovatech.com",
                    rol=ROL_EMPRESA,
                    empresa=empresa_mediana,
                )
                admin_med.set_password("Cliente123!")
                db.session.add(admin_med)

            db.session.commit()
            print("Empresas demo creadas.")

            from datetime import datetime

            ind_autoreportados = Indicador.query.filter_by(tipo_medicion="AUTOREPORTADO").all()

            respuestas_micro = {
                "¿Llevas un registro organizado de tus ingresos y gastos mensuales?": 25,
                "¿Cuál fue tu ingreso aproximado el último mes (en pesos)?": 20,
                "¿Cuentas con un presupuesto mensual definido?": 15,
                "¿Llevas un control organizado de tu inventario?": 30,
                "¿Tus procesos principales están documentados o estandarizados?": 10,
                "¿Qué porcentaje de tus ingresos proviene de canales digitales?": 15,
                "¿Tienes una base de datos de tus clientes?": 10,
                "¿Utilizas alguna herramienta para gestionar clientes (CRM)?": 5,
                "¿Mides la satisfacción de tus clientes?": 10,
                "¿Tu negocio tiene presencia online (página web, redes sociales)?": 35,
                "¿Utilizas herramientas digitales para gestionar tu negocio?": 20,
                "¿Vendes o promocionas tus productos/servicios por internet?": 15,
                "¿Generas reportes periódicos de tu negocio?": 10,
                "¿Tomas decisiones de negocio basadas en datos o estadísticas?": 5,
                "¿Cuentas con respaldos (backups) de tu información?": 20,
                "¿Tus empleados conocen buenas prácticas de seguridad digital?": 15,
                "¿Utilizas software para tareas repetitivas (contabilidad, inventario)?": 10,
                "¿Algunos de tus procesos se ejecutan automáticamente?": 5,
                "¿Revisas métricas o indicadores de tu negocio regularmente?": 15,
                "¿Utilizas herramientas de análisis (Excel avanzado, BI, dashboards)?": 10,
            }

            respuestas_mediana = {
                "¿Llevas un registro organizado de tus ingresos y gastos mensuales?": 80,
                "¿Cuál fue tu ingreso aproximado el último mes (en pesos)?": 75,
                "¿Cuentas con un presupuesto mensual definido?": 70,
                "¿Llevas un control organizado de tu inventario?": 65,
                "¿Tus procesos principales están documentados o estandarizados?": 60,
                "¿Qué porcentaje de tus ingresos proviene de canales digitales?": 85,
                "¿Tienes una base de datos de tus clientes?": 75,
                "¿Utilizas alguna herramienta para gestionar clientes (CRM)?": 70,
                "¿Mides la satisfacción de tus clientes?": 55,
                "¿Tu negocio tiene presencia online (página web, redes sociales)?": 90,
                "¿Utilizas herramientas digitales para gestionar tu negocio?": 80,
                "¿Vendes o promocionas tus productos/servicios por internet?": 75,
                "¿Generas reportes periódicos de tu negocio?": 70,
                "¿Tomas decisiones de negocio basadas en datos o estadísticas?": 65,
                "¿Cuentas con respaldos (backups) de tu información?": 85,
                "¿Tus empleados conocen buenas prácticas de seguridad digital?": 60,
                "¿Utilizas software para tareas repetitivas (contabilidad, inventario)?": 70,
                "¿Algunos de tus procesos se ejecutan automáticamente?": 55,
                "¿Revisas métricas o indicadores de tu negocio regularmente?": 75,
                "¿Utilizas herramientas de análisis (Excel avanzado, BI, dashboards)?": 65,
            }

            for ind in ind_autoreportados:
                texto = ind.texto
                if texto in respuestas_micro:
                    db.session.add(RespuestaDiagnostico(
                        empresa_id=empresa_micro.id, indicador_id=ind.id,
                        valor=respuestas_micro[texto], fecha=datetime.utcnow(),
                    ))
                if texto in respuestas_mediana:
                    db.session.add(RespuestaDiagnostico(
                        empresa_id=empresa_mediana.id, indicador_id=ind.id,
                        valor=respuestas_mediana[texto], fecha=datetime.utcnow(),
                    ))

            db.session.commit()

            def _calcular_y_guardar(empresa_id, respuestas_map):
                respuestas = RespuestaDiagnostico.query.filter_by(empresa_id=empresa_id).all()
                ind_map = {r.indicador_id: r for r in respuestas}
                indicadores = Indicador.query.filter(Indicador.id.in_(ind_map.keys())).all()
                dim_map = {}
                for ind in indicadores:
                    if ind.dimension_id not in dim_map:
                        dim_map[ind.dimension_id] = {"suma": 0, "peso_total": 0}
                    dim_map[ind.dimension_id]["suma"] += float(ind_map[ind.id].valor) * float(ind.peso)
                    dim_map[ind.dimension_id]["peso_total"] += float(ind.peso)

                for dim_id, data in dim_map.items():
                    if data["peso_total"] > 0:
                        puntaje = round(data["suma"] / data["peso_total"], 2)
                    else:
                        puntaje = 0
                    db.session.add(IndiceMadurez(
                        empresa_id=empresa_id, dimension_id=dim_id,
                        puntaje=puntaje, fecha=datetime.utcnow(),
                    ))
                db.session.commit()

            _calcular_y_guardar(empresa_micro.id, respuestas_micro)
            _calcular_y_guardar(empresa_mediana.id, respuestas_mediana)
            print("Respuestas de diagnóstico e índices de madurez creados.")

        print("Datos semilla listos.")

    return app


app = crear_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
