from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db import transaction

from .models import AlertaOperacional, Atividade, Colaborador, Equipe, Fazenda, Localizacao
from .openai_alert_service import gerar_texto_alerta_openai
from .weather_service import buscar_dados_climaticos


ATIVIDADES_PESADAS = {
    "preparar solo",
    "capinar",
    "colher",
    "colheita",
    "carregar",
    "operar maquina",
    "operar máquina",
}


@dataclass
class ClassificacaoRisco:
    nivel: str
    max_exposicao_horas: float
    pausa_a_cada_min: int


def limpar_alertas_antigos(localizacao: Localizacao) -> None:
    localizacao.alertas.all().delete()


@transaction.atomic
def salvar_localizacao_fazenda(
    fazenda: Fazenda,
    latitude: float,
    longitude: float,
    horario: str,
    endereco_aproximado: str = "",
) -> Localizacao:
    localizacao, _ = Localizacao.objects.update_or_create(
        fazenda=fazenda,
        defaults={
            "latitude": Decimal(str(latitude)),
            "longitude": Decimal(str(longitude)),
            "horario": horario,
            "endereco_aproximado": endereco_aproximado,
            "clima": "",
            "temperatura": None,
            "umidade": None,
            "indice_calor": None,
        },
    )

    limpar_alertas_antigos(localizacao)
    return localizacao


@transaction.atomic
def processar_dados_climaticos_fazenda(fazenda: Fazenda) -> Localizacao:
    localizacao = getattr(fazenda, "localizacao_ativa", None)
    if not localizacao:
        raise ValueError("Salve uma localização antes de processar dados climáticos.")

    dados = buscar_dados_climaticos(
        latitude=float(localizacao.latitude),
        longitude=float(localizacao.longitude),
    )

    localizacao.clima = dados.clima
    localizacao.temperatura = dados.temperatura
    localizacao.umidade = dados.umidade
    localizacao.indice_calor = dados.indice_calor
    localizacao.save(update_fields=["clima", "temperatura", "umidade", "indice_calor", "atualizado_em"])

    return localizacao


def classificar_risco(
    temperatura: float,
    umidade: int,
    indice_calor: float,
    jornada_horas: int,
    atividade_nome: str = "",
    intensidade_atividade: int = 5,
) -> ClassificacaoRisco:
    score = 0

    if temperatura >= 34 or indice_calor >= 41:
        score = 3
    elif temperatura >= 30 and umidade >= 60:
        score = 2
    elif temperatura >= 28 or indice_calor >= 32:
        score = 1

    if jornada_horas >= 7 and score >= 2:
        score = min(3, score + 1)

    intensidade = max(1, min(10, int(intensidade_atividade or 5)))
    if intensidade >= 9:
        score = min(3, score + 1)
    elif intensidade >= 7 and score >= 1:
        score = min(3, score + 1)
    elif intensidade >= 8 and score == 0:
        score = 1

    atividade_normalizada = atividade_nome.strip().lower()
    atividade_pesada = any(chave in atividade_normalizada for chave in ATIVIDADES_PESADAS) or intensidade >= 7

    nivel_map = {
        0: AlertaOperacional.Niveis.BAIXO,
        1: AlertaOperacional.Niveis.ATENCAO,
        2: AlertaOperacional.Niveis.ALTO,
        3: AlertaOperacional.Niveis.CRITICO,
    }
    exposicao_map = {0: 4.0, 1: 3.0, 2: 2.0, 3: 1.0}
    pausa_map = {0: 120, 1: 90, 2: 60, 3: 30}

    max_exposicao = exposicao_map[score]
    pausa = pausa_map[score]

    if atividade_pesada:
        max_exposicao = max(1.0, max_exposicao - 1.0)
        pausa = max(30, pausa - 30)
    elif intensidade >= 5:
        max_exposicao = max(1.0, max_exposicao - 0.5)
        pausa = max(30, pausa - 15)

    return ClassificacaoRisco(
        nivel=nivel_map[score],
        max_exposicao_horas=max_exposicao,
        pausa_a_cada_min=pausa,
    )


def montar_texto_alerta_padrao(
    alvo_nome: str,
    atividade_nome: str,
    intensidade_atividade: int,
    risco: ClassificacaoRisco,
) -> str:
    atividade = atividade_nome or "atividade operacional"
    return (
        f"{alvo_nome} não pode executar '{atividade}' (intensidade {intensidade_atividade}/10) por mais de "
        f"{risco.max_exposicao_horas:g}h seguidas. "
        f"Sugestão: pausas de 5 min a cada {risco.pausa_a_cada_min} min."
    )


def montar_texto_alerta(
    localizacao: Localizacao,
    alvo_nome: str,
    atividade_nome: str,
    intensidade_atividade: int,
    risco: ClassificacaoRisco,
    jornada_horas: int,
    tipo_alvo: str,
) -> str:
    contexto = {
        "tipo_alvo": tipo_alvo,
        "alvo_nome": alvo_nome,
        "atividade_nome": atividade_nome or "atividade operacional",
        "intensidade_atividade": intensidade_atividade,
        "nivel_risco": risco.nivel,
        "max_exposicao_horas": risco.max_exposicao_horas,
        "pausa_a_cada_min": risco.pausa_a_cada_min,
        "jornada_horas": jornada_horas,
        "clima": localizacao.clima,
        "temperatura_c": float(localizacao.temperatura or 0),
        "umidade_percentual": int(localizacao.umidade or 0),
        "indice_calor_c": float(localizacao.indice_calor or 0),
        "endereco_aproximado": localizacao.endereco_aproximado,
    }
    texto_openai = gerar_texto_alerta_openai(contexto)
    if texto_openai:
        return texto_openai

    return montar_texto_alerta_padrao(alvo_nome, atividade_nome, intensidade_atividade, risco)


def _atividade_principal_colaborador(colaborador: Colaborador) -> Optional[Atividade]:
    return colaborador.atividades.order_by("id").first()


def gerar_alerta_colaborador(localizacao: Localizacao, colaborador: Colaborador) -> AlertaOperacional:
    atividade = _atividade_principal_colaborador(colaborador)
    atividade_nome = atividade.nome if atividade else "atividade não informada"
    intensidade = atividade.intensidade if atividade else 5

    risco = classificar_risco(
        temperatura=float(localizacao.temperatura or 0),
        umidade=int(localizacao.umidade or 0),
        indice_calor=float(localizacao.indice_calor or 0),
        jornada_horas=colaborador.jornada_horas,
        atividade_nome=atividade_nome,
        intensidade_atividade=intensidade,
    )

    texto = montar_texto_alerta(
        localizacao=localizacao,
        alvo_nome=colaborador.nome,
        atividade_nome=atividade_nome,
        intensidade_atividade=intensidade,
        risco=risco,
        jornada_horas=colaborador.jornada_horas,
        tipo_alvo="colaborador",
    )

    return AlertaOperacional.objects.create(
        localizacao=localizacao,
        colaborador=colaborador,
        texto=texto,
        nivel=risco.nivel,
    )


def gerar_alerta_equipe(localizacao: Localizacao, equipe: Equipe) -> Optional[AlertaOperacional]:
    colaboradores = list(equipe.colaboradores.prefetch_related("atividades"))
    if not colaboradores:
        return None

    maior_risco = None
    atividade_referencia = "atividade operacional"
    intensidade_referencia = 5
    jornada_referencia = 8

    for colaborador in colaboradores:
        atividade = _atividade_principal_colaborador(colaborador)
        atividade_nome = atividade.nome if atividade else "atividade não informada"
        intensidade = atividade.intensidade if atividade else 5

        risco = classificar_risco(
            temperatura=float(localizacao.temperatura or 0),
            umidade=int(localizacao.umidade or 0),
            indice_calor=float(localizacao.indice_calor or 0),
            jornada_horas=colaborador.jornada_horas,
            atividade_nome=atividade_nome,
            intensidade_atividade=intensidade,
        )

        if maior_risco is None or _peso_nivel(risco.nivel) > _peso_nivel(maior_risco.nivel):
            maior_risco = risco
            atividade_referencia = atividade_nome
            intensidade_referencia = intensidade
            jornada_referencia = colaborador.jornada_horas

    if maior_risco is None:
        return None

    texto = montar_texto_alerta(
        localizacao=localizacao,
        alvo_nome=f"Equipe {equipe.nome}",
        atividade_nome=atividade_referencia,
        intensidade_atividade=intensidade_referencia,
        risco=maior_risco,
        jornada_horas=jornada_referencia,
        tipo_alvo="equipe",
    )

    return AlertaOperacional.objects.create(
        localizacao=localizacao,
        equipe=equipe,
        texto=texto,
        nivel=maior_risco.nivel,
    )


def _peso_nivel(nivel: str) -> int:
    pesos = {
        AlertaOperacional.Niveis.BAIXO: 0,
        AlertaOperacional.Niveis.ATENCAO: 1,
        AlertaOperacional.Niveis.ALTO: 2,
        AlertaOperacional.Niveis.CRITICO: 3,
    }
    return pesos.get(nivel, 0)


@transaction.atomic
def processar_alertas_fazenda(fazenda: Fazenda):
    localizacao = getattr(fazenda, "localizacao_ativa", None)
    if not localizacao:
        raise ValueError("Salve uma localização antes de processar alertas.")

    if localizacao.temperatura is None or localizacao.umidade is None or localizacao.indice_calor is None:
        raise ValueError("Processe os dados climáticos antes de gerar alertas.")

    limpar_alertas_antigos(localizacao)

    alertas = []
    equipes = list(fazenda.equipes.prefetch_related("colaboradores__atividades"))

    if equipes:
        for equipe in equipes:
            alerta = gerar_alerta_equipe(localizacao, equipe)
            if alerta:
                alertas.append(alerta)

        colaboradores_sem_equipe = fazenda.colaboradores.filter(equipe__isnull=True).prefetch_related("atividades")
        for colaborador in colaboradores_sem_equipe:
            alertas.append(gerar_alerta_colaborador(localizacao, colaborador))
    else:
        colaboradores = fazenda.colaboradores.prefetch_related("atividades")
        for colaborador in colaboradores:
            alertas.append(gerar_alerta_colaborador(localizacao, colaborador))

    return alertas
