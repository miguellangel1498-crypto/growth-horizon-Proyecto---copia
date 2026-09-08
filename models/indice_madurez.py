from datetime import datetime

from extensions import db


class IndiceMadurez(db.Model):
    __tablename__ = "indices_madurez"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    dimension_id = db.Column(db.Integer, db.ForeignKey("dimensiones.id", ondelete="CASCADE"), nullable=False, index=True)
    puntaje = db.Column(db.Numeric(5, 2), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    empresa = db.relationship("Empresa", backref=db.backref("indices_madurez", lazy="dynamic"))
    dimension = db.relationship("Dimension", backref=db.backref("indices", lazy="dynamic"))

    def __repr__(self):
        return f"<IndiceMadurez empresa={self.empresa_id} dim={self.dimension_id} puntaje={self.puntaje}>"
