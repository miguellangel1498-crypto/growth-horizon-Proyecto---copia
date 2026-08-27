from extensions import db


class Configuracion(db.Model):
    __tablename__ = "configuracion"

    clave = db.Column(db.String(80), primary_key=True)
    valor = db.Column(db.Text, nullable=True)
    descripcion = db.Column(db.String(255), nullable=True)

    @staticmethod
    def obtener(clave, defecto=None):
        registro = db.session.get(Configuracion, clave)
        if registro is None:
            return defecto
        return registro.valor

    @staticmethod
    def poner(clave, valor, descripcion=None):
        registro = db.session.get(Configuracion, clave)
        if registro is None:
            registro = Configuracion(clave=clave, descripcion=descripcion)
            db.session.add(registro)
        registro.valor = valor
        if descripcion is not None:
            registro.descripcion = descripcion
        return registro

    @staticmethod
    def boolean(clave, defecto=True):
        valor = Configuracion.obtener(clave)
        if valor is None:
            return defecto
        return valor.lower() in ("1", "true", "si", "s", "on", "yes", "activo")
