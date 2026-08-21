from extensions import db
from models.base import TimestampMixin


class Producto(TimestampMixin, db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre = db.Column(db.String(180), nullable=False)
    categoria = db.Column(db.String(120), nullable=True, index=True)
    precio = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    empresa = db.relationship("Empresa", backref=db.backref("productos", lazy="dynamic"))
    ventas = db.relationship("Venta", backref="producto", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Producto {self.nombre}>"