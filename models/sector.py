from extensions import db
from models.base import TimestampMixin


class Sector(TimestampMixin, db.Model):
    __tablename__ = "sectores"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(20), nullable=False, default="#0891b2")

    empresas = db.relationship("Empresa", backref="sector", lazy="dynamic", passive_deletes=True)

    def __repr__(self):
        return f"<Sector {self.nombre}>"