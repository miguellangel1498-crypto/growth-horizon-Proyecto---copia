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
            return current_user.get_id()
    except Exception:
        pass
    return None


def registrar(accion, entidad=None, entidad_id=None, detalle=None):
    ctx = _contexto_request()
    registro = Auditoria(
        usuario_id=_usuario_actual_id(),
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        detalle=detalle,
        ip_address=ctx["ip"],
        user_agent=ctx["ua"],
    )
    db.session.add(registro)
    return registro


def registrar_y_commit(accion, entidad=None, entidad_id=None, detalle=None):
    registro = registrar(accion, entidad, entidad_id, detalle)
    db.session.commit()
    return registro


def registrar_login(usuario, exitoso=True, motivo=None):
    detalle = f"Acceso de {usuario.email} ({usuario.rol})"
    if motivo:
        detalle = f"{detalle} - {motivo}"
    accion = "LOGIN_EXITOSO" if exitoso else "LOGIN_FALLIDO"
    return registrar(
        accion=accion,
        entidad="Usuario",
        entidad_id=usuario.id if usuario else None,
        detalle=detalle,
    )


def registrar_login_fallido(usuario, motivo=None):
    intentos = usuario.intentos_fallidos
    if intentos <= 3:
        return None
    detalle = f"Acceso de {usuario.email} ({usuario.rol}) - {intentos} intentos fallidos"
    if motivo:
        detalle = f"{detalle} - {motivo}"
    return registrar(
        accion="LOGIN_FALLIDO",
        entidad="Usuario",
        entidad_id=usuario.id,
        detalle=detalle,
    )


def registrar_alerta_superadmin(usuario, motivo=None):
    detalle = f"ALERTA CRITICA: Intento de acceso fallido a cuenta superadmin ({usuario.email})"
    if motivo:
        detalle = f"{detalle} - {motivo}"
    ctx = _contexto_request()
    return Auditoria(
        usuario_id=usuario.id,
        accion="ALERTA_SUPERADMIN",
        entidad="Usuario",
        entidad_id=usuario.id,
        detalle=detalle,
        ip_address=ctx["ip"],
        user_agent=ctx["ua"],
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

        ctx = _contexto_request()
        usuario_id = _usuario_actual_id()

        for obj, accion, detalle in pendientes:
            sesion.add(
                Auditoria(
                    usuario_id=usuario_id,
                    accion=accion,
                    entidad=obj.__class__.__name__,
                    entidad_id=obj.id,
                    detalle=detalle,
                    ip_address=ctx["ip"],
                    user_agent=ctx["ua"],
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
            if nombre in {"created_at", "updated_at"}:
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