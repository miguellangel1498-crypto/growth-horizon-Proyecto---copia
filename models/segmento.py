from extensions import db
from models.base import TimestampMixin


class Segmento(TimestampMixin, db.Model):
    __tablename__ = "segmentos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    rango_min = db.Column(db.Numeric(5, 2), nullable=False)
    rango_max = db.Column(db.Numeric(5, 2), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Segmento {self.nombre}>"
