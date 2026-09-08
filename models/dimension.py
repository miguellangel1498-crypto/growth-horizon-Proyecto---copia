from extensions import db
from models.base import TimestampMixin


class Dimension(TimestampMixin, db.Model):
    __tablename__ = "dimensiones"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.Text, nullable=True)
    peso = db.Column(db.Numeric(5, 2), nullable=False, default=1.0)

    indicadores = db.relationship("Indicador", backref="dimension", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Dimension {self.nombre}>"
