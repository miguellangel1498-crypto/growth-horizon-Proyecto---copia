from flask_login import UserMixin

from extensions import db
from models.base import TimestampMixin


class Usuario(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(40), nullable=False, default="analista")
    activo = db.Column(db.Boolean, nullable=False, default=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectores.id"), nullable=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True)
    ultimo_acceso = db.Column(db.DateTime, nullable=True)

    sector = db.relationship("Sector", backref=db.backref("usuarios", lazy="dynamic", passive_deletes=True))
    empresa = db.relationship("Empresa", backref=db.backref("usuarios", lazy="dynamic", passive_deletes=True))
    auditorias = db.relationship("Auditoria", backref="usuario", lazy="dynamic")

    def set_password(self, password):
        from extensions import bcrypt

        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        from extensions import bcrypt

        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def es_admin(self):
        return self.rol == "admin"

    @property
    def es_empresa(self):
        return self.empresa is not None

    def __repr__(self):
        return f"<Usuario {self.email}>"