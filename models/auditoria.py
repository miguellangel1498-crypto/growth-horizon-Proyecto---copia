from datetime import datetime

from extensions import db


class Auditoria(db.Model):
    __tablename__ = "auditoria"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    accion = db.Column(db.String(60), nullable=False, index=True)
    entidad = db.Column(db.String(60), nullable=True)
    entidad_id = db.Column(db.Integer, nullable=True)
    detalle = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<Auditoria {self.accion} {self.created_at}>"