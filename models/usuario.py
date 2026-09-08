from flask_login import UserMixin

from extensions import db
from models.base import TimestampMixin
from models.roles import (
    ROL_ANALISTA,
    ROL_EMPLEADO,
    ROL_EMPRESA,
    ROL_SUPERADMIN,
    rol_tiene_permiso,
)


class Usuario(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(40), nullable=False, default=ROL_ANALISTA)
    cargo = db.Column(db.String(80), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectores.id"), nullable=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True)
    ultimo_acceso = db.Column(db.DateTime, nullable=True)
    intentos_fallidos = db.Column(db.Integer, nullable=False, default=0)
    ultimo_intento_fallido = db.Column(db.DateTime, nullable=True)

    sector = db.relationship("Sector", backref=db.backref("usuarios", lazy="dynamic", passive_deletes=True))
    empresa = db.relationship("Empresa", backref=db.backref("usuarios", lazy="dynamic", passive_deletes=True))
    auditorias = db.relationship("Auditoria", backref="usuario", lazy="dynamic")

    def set_password(self, password):
        from extensions import bcrypt

        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        from extensions import bcrypt

        return bcrypt.check_password_hash(self.password_hash, password)

    def incrementar_intentos_fallidos(self):
        from datetime import datetime

        self.intentos_fallidos += 1
        self.ultimo_intento_fallido = datetime.utcnow()
        return self.intentos_fallidos

    def resetear_intentos_fallidos(self):
        self.intentos_fallidos = 0
        self.ultimo_intento_fallido = None

    @property
    def es_superadmin(self):
        return self.rol == ROL_SUPERADMIN

    @property
    def es_admin_empresa(self):
        return self.rol == ROL_EMPRESA

    @property
    def es_empleado(self):
        return self.rol == ROL_EMPLEADO

    @property
    def es_empleado_activo(self):
        return self.rol == ROL_EMPLEADO and self.activo

    @property
    def es_admin(self):
        return self.rol in (ROL_SUPERADMIN, ROL_EMPRESA)

    @property
    def tiene_empresa(self):
        return self.empresa is not None

    @property
    def es_empresa(self):
        return self.tiene_empresa

    @property
    def acceso_empresa_activa(self):
        return self.empresa is None or self.empresa.estado == "activo"

    @property
    def puede_ver_finanzas(self):
        return rol_tiene_permiso(self.rol, "Reportes financieros (COP)")

    @property
    def puede_administrar(self):
        return rol_tiene_permiso(self.rol, "Configuración y horarios")

    @property
    def puede_gestionar_empleados(self):
        return rol_tiene_permiso(self.rol, "Gestionar empleados")

    @property
    def etiqueta_rol(self):
        from models.roles import ROLES_DISPONIBLES

        return ROLES_DISPONIBLES.get(self.rol, self.rol)

    def tiene_permiso(self, clave):
        return rol_tiene_permiso(self.rol, clave)

    def __repr__(self):
        return f"<Usuario {self.email}>"