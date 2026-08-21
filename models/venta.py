from datetime import datetime

from extensions import db


class Venta(db.Model):
    __tablename__ = "ventas"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id", ondelete="SET NULL"), nullable=True)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    empresa = db.relationship("Empresa", backref=db.backref("ventas", lazy="dynamic"))

    @property
    def total(self):
        return (self.precio_unitario or 0) * (self.cantidad or 0)

    def __repr__(self):
        return f"<Venta #{self.id} total={self.total}>"