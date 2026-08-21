from extensions import db
from models.base import TimestampMixin

DIAS_SEMANA = [
    ("Lunes", 0),
    ("Martes", 1),
    ("Miércoles", 2),
    ("Jueves", 3),
    ("Viernes", 4),
    ("Sábado", 5),
    ("Domingo", 6),
]


class HorarioAtencion(TimestampMixin, db.Model):
    __tablename__ = "horarios_atencion"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    dia = db.Column(db.String(20), nullable=False)
    dia_numero = db.Column(db.Integer, nullable=False, default=0)
    apertura = db.Column(db.String(5), nullable=False, default="09:00")
    cierre = db.Column(db.String(5), nullable=False, default="18:00")

    empresa = db.relationship("Empresa", backref=db.backref("horarios", lazy="dynamic"))

    @property
    def rango(self):
        return f"{self.apertura} - {self.cierre}"

    def __repr__(self):
        return f"<Horario {self.dia} {self.rango}>"