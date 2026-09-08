from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Dimension, IndiceMadurez, Indicador, Recomendacion, RespuestaDiagnostico, Segmento
from models.roles import ROL_EMPRESA
from routes.decoradores import admin_empresa_requerido

diagnostico_bp = Blueprint("diagnostico", __name__, url_prefix="/diagnostico")


def _empresa_id():
    if current_user.empresa is None:
        abort(403)
    if not current_user.acceso_empresa_activa:
        abort(403)
    return current_user.empresa.id


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


def _guardar_indice_snapshot(empresa_id, dim_puntajes):
    for dim_id, data in dim_puntajes.items():
        snapshot = IndiceMadurez(
            empresa_id=empresa_id,
            dimension_id=dim_id,
            puntaje=data["puntaje"],
            fecha=datetime.utcnow(),
        )
        db.session.add(snapshot)


@diagnostico_bp.route("/responder", methods=["GET", "POST"])
@login_required
@admin_empresa_requerido
def responder():
    empresa_id = _empresa_id()

    if request.method == "POST":
        indicadores = Indicador.query.filter_by(tipo_medicion="AUTOREPORTADO").all()

        for ind in indicadores:
            valor_str = request.form.get(f"indicador_{ind.id}", "").strip()
            if valor_str:
                try:
                    valor = float(valor_str)
                    valor = max(0, min(100, valor))
                except ValueError:
                    continue

                existente = RespuestaDiagnostico.query.filter_by(
                    empresa_id=empresa_id, indicador_id=ind.id
                ).first()

                if existente:
                    existente.valor = valor
                    existente.fecha = datetime.utcnow()
                else:
                    respuesta = RespuestaDiagnostico(
                        empresa_id=empresa_id,
                        indicador_id=ind.id,
                        valor=valor,
                        fecha=datetime.utcnow(),
                    )
                    db.session.add(respuesta)

        db.session.commit()

        indice_general, dim_puntajes = _calcular_indice_empresa(empresa_id)
        if dim_puntajes:
            _guardar_indice_snapshot(empresa_id, dim_puntajes)
            db.session.commit()

        flash("Diagnóstico guardado correctamente.", "success")
        return redirect(url_for("diagnostico.resultados"))

    dimensiones = Dimension.query.order_by(Dimension.nombre.asc()).all()
    indicadores_autoreportado = Indicador.query.filter_by(tipo_medicion="AUTOREPORTADO").all()

    respuestas_existentes = {}
    respuestas_db = RespuestaDiagnostico.query.filter_by(empresa_id=empresa_id).all()
    for r in respuestas_db:
        respuestas_existentes[r.indicador_id] = float(r.valor)

    indicadores_por_dim = {}
    for ind in indicadores_autoreportado:
        if ind.dimension_id not in indicadores_por_dim:
            indicadores_por_dim[ind.dimension_id] = []
        indicadores_por_dim[ind.dimension_id].append(ind)

    return render_template(
        "diagnostico/responder.html",
        empresa=current_user.empresa,
        dimensiones=dimensiones,
        indicadores_por_dim=indicadores_por_dim,
        respuestas_existentes=respuestas_existentes,
    )


@diagnostico_bp.route("/resultados")
@login_required
@admin_empresa_requerido
def resultados():
    empresa_id = _empresa_id()
    empresa = current_user.empresa

    indice_general, dim_puntajes = _calcular_indice_empresa(empresa_id)

    segmento = None
    if indice_general is not None:
        segmento = (
            Segmento.query
            .filter(Segmento.rango_min <= indice_general, Segmento.rango_max >= indice_general)
            .first()
        )

    from models import Empresa, IndiceMadurez as IM

    promedio_sector = None
    if empresa.sector_id:
        empresas_sector = Empresa.query.filter(
            Empresa.sector_id == empresa.sector_id,
            Empresa.tamano_empresa == empresa.tamano_empresa,
            Empresa.estado == "activo",
        ).all()
        if empresas_sector:
            empresa_ids = [e.id for e in empresas_sector]
            from sqlalchemy import func
            promedio_sector = (
                db.session.query(func.avg(IM.puntaje))
                .filter(IM.empresa_id.in_(empresa_ids))
                .scalar()
            )
            promedio_sector = round(float(promedio_sector), 2) if promedio_sector else None

    recomendaciones_dim = {}
    if dim_puntajes:
        for dim_id, data in dim_puntajes.items():
            recs = (
                Recomendacion.query
                .filter(
                    Recomendacion.dimension_id == dim_id,
                    Recomendacion.rango_min <= data["puntaje"],
                    Recomendacion.rango_max >= data["puntaje"],
                )
                .all()
            )
            if recs:
                recomendaciones_dim[dim_id] = recs

    historial = (
        IM.query
        .filter_by(empresa_id=empresa_id)
        .order_by(IM.fecha.asc())
        .all()
    )

    return render_template(
        "diagnostico/resultados.html",
        empresa=empresa,
        indice_general=indice_general,
        dim_puntajes=dim_puntajes,
        segmento=segmento,
        promedio_sector=promedio_sector,
        recomendaciones_dim=recomendaciones_dim,
        historial=historial,
    )
