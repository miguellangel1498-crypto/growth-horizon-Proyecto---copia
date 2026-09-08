from datetime import datetime

from extensions import db


class RespuestaDiagnostico(db.Model):
    __tablename__ = "respuestas_diagnostico"
    __table_args__ = (
        db.UniqueConstraint("empresa_id", "indicador_id", name="uq_empresa_indicador"),
    )

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    indicador_id = db.Column(db.Integer, db.ForeignKey("indicadores.id", ondelete="CASCADE"), nullable=False, index=True)
    valor = db.Column(db.Numeric(5, 2), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    empresa = db.relationship("Empresa", backref=db.backref("respuestas_diagnostico", lazy="dynamic"))
    indicador = db.relationship("Indicador", backref=db.backref("respuestas", lazy="dynamic"))

    def __repr__(self):
        return f"<RespuestaDiagnostico empresa={self.empresa_id} indicador={self.indicador_id} valor={self.valor}>"
