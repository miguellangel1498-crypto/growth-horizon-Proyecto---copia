from extensions import db
from models.base import TimestampMixin


class Empresa(TimestampMixin, db.Model):
    __tablename__ = "empresas"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(180), nullable=False, index=True)
    ruc = db.Column(db.String(20), unique=True, nullable=True, index=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectores.id", ondelete="SET NULL"), nullable=True)
    actividad = db.Column(db.String(255), nullable=True)
    correo = db.Column(db.String(180), nullable=True)
    telefono = db.Column(db.String(40), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    sitio_web = db.Column(db.String(255), nullable=True)
    estado = db.Column(db.String(20), nullable=False, default="activo")

    def __repr__(self):
        return f"<Empresa {self.nombre}>"