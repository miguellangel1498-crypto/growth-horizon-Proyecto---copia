from extensions import db
from models.base import TimestampMixin


class Indicador(TimestampMixin, db.Model):
    __tablename__ = "indicadores"

    id = db.Column(db.Integer, primary_key=True)
    dimension_id = db.Column(db.Integer, db.ForeignKey("dimensiones.id", ondelete="CASCADE"), nullable=False, index=True)
    texto = db.Column(db.Text, nullable=False)
    peso = db.Column(db.Numeric(5, 2), nullable=False, default=1.0)
    tipo_medicion = db.Column(db.String(20), nullable=False, default="AUTOREPORTADO")

    def __repr__(self):
        return f"<Indicador {self.id} {self.tipo_medicion}>"
