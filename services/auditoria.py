from sqlalchemy import event

from extensions import db
from models.auditoria import Auditoria
from models.empresa import Empresa
from models.sector import Sector


def _contexto_request():
    from flask import has_request_context, request

    if not has_request_context():
        return {"ip": None, "ua": None}

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip:
        ip = ip.split(",")[0].strip()
    ua = (request.user_agent.string or "")[:255] if request.user_agent else None
    return {"ip": ip, "ua": ua}


def _usuario_actual_id():
    from flask_login import current_user

    try:
        if current_user.is_authenticated:
            return current_user.id_usuario
    except Exception:
        pass
    return None


def registrar(accion, tabla_afectada=None, id_registro=None, descripcion=None):
    ctx = _contexto_request()
    registro = Auditoria(
        id_usuario=_usuario_actual_id(),
        accion=accion,
        tabla_afectada=tabla_afectada,
        id_registro=id_registro,
        descripcion=descripcion,
        direccion_ip=ctx["ip"],
    )
    db.session.add(registro)
    return registro


def registrar_y_commit(accion, tabla_afectada=None, id_registro=None, descripcion=None):
    registro = registrar(accion, tabla_afectada, id_registro, descripcion)
    db.session.commit()
    return registro


def registrar_login(usuario, exitoso=True, motivo=None):
    detalle = f"Acceso de {usuario.correo}"
    if motivo:
        detalle = f"{detalle} - {motivo}"
    accion = "LOGIN_EXITOSO" if exitoso else "LOGIN_FALLIDO"
    return registrar(
        accion=accion,
        tabla_afectada="usuarios",
        id_registro=usuario.id_usuario,
        descripcion=detalle,
    )


def registrar_login_fallido(usuario, motivo=None):
    detalle = f"Acceso fallido de {usuario.correo}"
    if motivo:
        detalle = f"{detalle} - {motivo}"
    return registrar(
        accion="LOGIN_FALLIDO",
        tabla_afectada="usuarios",
        id_registro=usuario.id_usuario,
        descripcion=detalle,
    )


def registrar_alerta_superadmin(usuario, motivo=None):
    detalle = f"ALERTA: Intento de acceso fallido a cuenta superadmin ({usuario.correo})"
    if motivo:
        detalle = f"{detalle} - {motivo}"
    return registrar(
        accion="ALERTA_SUPERADMIN",
        tabla_afectada="usuarios",
        id_registro=usuario.id_usuario,
        descripcion=detalle,
    )


class AutoAuditoria:
    MODELOS_VIGILADOS = (Empresa, Sector)

    @classmethod
    def configurar(cls):
        event.listen(db.session, "before_flush", cls._antes_del_flush)
        event.listen(db.session, "after_flush", cls._despues_del_flush)

    @classmethod
    def _antes_del_flush(cls, sesion, flush_context, instancias=None):
        if not cls._activo():
            return

        pendientes = []
        for obj in sesion.new:
            if isinstance(obj, cls.MODELOS_VIGILADOS):
                pendientes.append((obj, "INSERT", None))
        for obj in sesion.dirty:
            if isinstance(obj, cls.MODELOS_VIGILADOS) and sesion.is_modified(obj, include_collections=False):
                pendientes.append((obj, "UPDATE", cls._cambios(obj)))
        for obj in sesion.deleted:
            if isinstance(obj, cls.MODELOS_VIGILADOS):
                pendientes.append((obj, "DELETE", None))

        if pendientes:
            sesion.info["_gh_audit_pendientes"] = pendientes

    @classmethod
    def _despues_del_flush(cls, sesion, flush_context):
        pendientes = sesion.info.pop("_gh_audit_pendientes", [])
        if not pendientes:
            return

        usuario_id = _usuario_actual_id()

        for obj, accion, detalle in pendientes:
            id_col = getattr(obj, "id_empresa", None) or getattr(obj, "id_sector", None) or 0
            sesion.add(
                Auditoria(
                    id_usuario=usuario_id,
                    accion=accion,
                    tabla_afectada=obj.__tablename__,
                    id_registro=id_col,
                    descripcion=detalle,
                )
            )

    @staticmethod
    def _activo():
        from flask import has_request_context
        from flask_login import current_user

        if not has_request_context():
            return False
        try:
            return current_user.is_authenticated
        except Exception:
            return False

    @staticmethod
    def _cambios(obj):
        state = db.inspect(obj)
        cambios = {}
        for col in obj.__table__.columns:
            nombre = col.key
            if nombre in {"created_at", "updated_at", "fecha", "fecha_registro"}:
                continue
            try:
                historia = state.attrs[nombre].history
            except Exception:
                continue
            if historia.has_changes():
                anterior = historia.deleted[0] if historia.deleted else (
                    historia.unchanged[-1] if historia.unchanged else None
                )
                nuevo = historia.added[0] if historia.added else None
                if anterior != nuevo:
                    cambios[nombre] = {"anterior": anterior, "nuevo": nuevo}
        import json
        return json.dumps(cambios, ensure_ascii=False, default=str)
