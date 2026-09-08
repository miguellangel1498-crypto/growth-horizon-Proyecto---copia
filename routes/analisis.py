from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from extensions import db
from models import Dimension, Empresa, IndiceMadurez, Indicador, Recomendacion, RespuestaDiagnostico, Sector, Segmento
from models.roles import ROL_EMPRESA, ROL_SUPERADMIN

analisis_bp = Blueprint("analisis", __name__, url_prefix="/analisis")


def _calcular_indice_empresa(empresa_id):
    respuestas = (
        RespuestaDiagnostico.query
        .filter_by(empresa_id=empresa_id)
        .all()
    )
    if not respuestas:
        return None, {}

    indicador_ids = [r.indicador_id for r in respuestas]
    indicadores = Indicador.query.filter(Indicador.id.in_(indicador_ids)).all()
    ind_map = {i.id: i for i in indicadores}

    dimensiones = Dimension.query.all()
    dim_map = {d.id: d for d in dimensiones}

    peso_total_global = 0
    suma_ponderada_global = 0

    dim_puntajes = {}

    for resp in respuestas:
        ind = ind_map.get(resp.indicador_id)
        if ind is None:
            continue
        dim = dim_map.get(ind.dimension_id)
        if dim is None:
            continue

        peso_ind = float(ind.peso or 1)
        peso_dim = float(dim.peso or 1)

        if dim.id not in dim_puntajes:
            dim_puntajes[dim.id] = {
                "nombre": dim.nombre,
                "suma": 0,
                "peso_total": 0,
                "peso_dim": peso_dim,
            }

        dim_puntajes[dim.id]["suma"] += float(resp.valor) * peso_ind
        dim_puntajes[dim.id]["peso_total"] += peso_ind

    resultados_dim = {}
    for dim_id, data in dim_puntajes.items():
        if data["peso_total"] > 0:
            puntaje_dim = data["suma"] / data["peso_total"]
        else:
            puntaje_dim = 0
        resultados_dim[dim_id] = {
            "nombre": data["nombre"],
            "puntaje": round(puntaje_dim, 2),
            "peso": data["peso_dim"],
        }
        suma_ponderada_global += puntaje_dim * data["peso_dim"]
        peso_total_global += data["peso_dim"]

    if peso_total_global > 0:
        indice_general = round(suma_ponderada_global / peso_total_global, 2)
    else:
        indice_general = 0

    return indice_general, resultados_dim


def _obtener_segmento(puntaje):
    segmento = (
        Segmento.query
        .filter(Segmento.rango_min <= puntaje, Segmento.rango_max >= puntaje)
        .first()
    )
    return segmento


def _obtener_recomendaciones(dimension_id, puntaje):
    recs = (
        Recomendacion.query
        .filter(
            Recomendacion.dimension_id == dimension_id,
            Recomendacion.rango_min <= puntaje,
            Recomendacion.rango_max >= puntaje,
        )
        .all()
    )
    return recs


def _calcular_promedio_sector(sector_id, tamano_empresa):
    empresas_sector = Empresa.query.filter(
        Empresa.sector_id == sector_id,
        Empresa.tamano_empresa == tamano_empresa,
        Empresa.estado == "activo",
    ).all()

    if not empresas_sector:
        return None

    empresa_ids = [e.id for e in empresas_sector]
    indices = (
        IndiceMadurez.query
        .filter(IndiceMadurez.empresa_id.in_(empresa_ids))
        .all()
    )

    if not indices:
        return None

    from sqlalchemy import func

    promedio = (
        db.session.query(func.avg(IndiceMadurez.puntaje))
        .filter(IndiceMadurez.empresa_id.in_(empresa_ids))
        .scalar()
    )
    return round(float(promedio), 2) if promedio else None


def _ranking_empresas():
    from sqlalchemy import func

    ranking = (
        db.session.query(
            Empresa.id,
            Empresa.nombre,
            Empresa.tamano_empresa,
            func.avg(IndiceMadurez.puntaje).label("promedio"),
        )
        .join(IndiceMadurez, IndiceMadurez.empresa_id == Empresa.id)
        .filter(Empresa.estado == "activo")
        .group_by(Empresa.id, Empresa.nombre, Empresa.tamano_empresa)
        .order_by(func.avg(IndiceMadurez.puntaje).desc())
        .all()
    )
    return ranking


@analisis_bp.route("/")
@login_required
def principal():
    if current_user.rol not in (ROL_SUPERADMIN, ROL_EMPRESA):
        abort(403)
    if current_user.rol == ROL_EMPRESA and not current_user.activo:
        abort(403)
    if current_user.rol == ROL_EMPRESA and current_user.empresa is not None and not current_user.acceso_empresa_activa:
        abort(403)

    empresa = current_user.empresa
    es_admin = current_user.rol == ROL_SUPERADMIN

    if es_admin:
        ranking = _ranking_empresas()
        empresas_con_indice = []
        for emp_id, nombre, tamano, promedio in ranking:
            seg = _obtener_segmento(float(promedio))
            empresas_con_indice.append({
                "id": emp_id,
                "nombre": nombre,
                "tamano": tamano,
                "promedio": round(float(promedio), 2),
                "segmento": seg.nombre if seg else "Sin segmento",
            })

        todas_empresas = Empresa.query.filter_by(estado="activo").all()
        return render_template(
            "analisis.html",
            es_admin=True,
            empresa=None,
            empresas_con_indice=empresas_con_indice,
            todas_empresas=todas_empresas,
        )
    else:
        if empresa is None:
            abort(403)

        indice_general, dim_puntajes = _calcular_indice_empresa(empresa.id)
        segmento = _obtener_segmento(indice_general) if indice_general is not None else None

        promedio_sector = _calcular_promedio_sector(empresa.sector_id, empresa.tamano_empresa)

        recomendaciones_dim = {}
        if dim_puntajes:
            for dim_id, data in dim_puntajes.items():
                recs = _obtener_recomendaciones(dim_id, data["puntaje"])
                if recs:
                    recomendaciones_dim[dim_id] = recs

        historial = (
            IndiceMadurez.query
            .filter_by(empresa_id=empresa.id)
            .order_by(IndiceMadurez.fecha.asc())
            .all()
        )

        return render_template(
            "analisis.html",
            es_admin=False,
            empresa=empresa,
            indice_general=indice_general,
            dim_puntajes=dim_puntajes,
            segmento=segmento,
            promedio_sector=promedio_sector,
            recomendaciones_dim=recomendaciones_dim,
            historial=historial,
        )
