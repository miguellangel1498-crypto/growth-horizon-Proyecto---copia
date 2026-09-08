from extensions import db
from models.base import TimestampMixin


class Recomendacion(TimestampMixin, db.Model):
    __tablename__ = "recomendaciones"

    id = db.Column(db.Integer, primary_key=True)
    dimension_id = db.Column(db.Integer, db.ForeignKey("dimensiones.id", ondelete="CASCADE"), nullable=False, index=True)
    rango_min = db.Column(db.Numeric(5, 2), nullable=False)
    rango_max = db.Column(db.Numeric(5, 2), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    prioridad = db.Column(db.String(20), nullable=False, default="MEDIA")

    dimension = db.relationship("Dimension", backref=db.backref("recomendaciones", lazy="dynamic"))

    def __repr__(self):
        return f"<Recomendacion dim={self.dimension_id} prioridad={self.prioridad}>"
