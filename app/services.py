from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db import transaction

from .models import AlertaOperacional, Atividade, Colaborador, Equipe, Fazenda, Localizacao
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
def atualizar_localizacao_fazenda(
    fazenda: Fazenda,
    latitude: float,
    longitude: float,
    horario: str,
) -> Localizacao:
    dados = buscar_dados_climaticos(latitude=latitude, longitude=longitude)

    localizacao, _ = Localizacao.objects.update_or_create(
        fazenda=fazenda,
        defaults={
            "latitude": Decimal(str(latitude)),
            "longitude": Decimal(str(longitude)),
            "horario": horario,
            "clima": dados.clima,
            "temperatura": dados.temperatura,
            "umidade": dados.umidade,
            "indice_calor": dados.indice_calor,
        },
    )

    limpar_alertas_antigos(localizacao)
    return localizacao


def classificar_risco(
    temperatura: float,
    umidade: int,
    indice_calor: float,
    jornada_horas: int,
    atividade_nome: str = "",
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

    atividade_normalizada = atividade_nome.strip().lower()
    atividade_pesada = any(chave in atividade_normalizada for chave in ATIVIDADES_PESADAS)

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

    return ClassificacaoRisco(
        nivel=nivel_map[score],
        max_exposicao_horas=max_exposicao,
        pausa_a_cada_min=pausa,
    )


def montar_texto_alerta(
    alvo_nome: str,
    atividade_nome: str,
    risco: ClassificacaoRisco,
) -> str:
    atividade = atividade_nome or "atividade operacional"
    return (
        f"{alvo_nome} não pode executar '{atividade}' por mais de "
        f"{risco.max_exposicao_horas:g}h seguidas. "
        f"Sugestão: pausas de 5 min a cada {risco.pausa_a_cada_min} min."
    )


def _atividade_principal_colaborador(colaborador: Colaborador) -> Optional[Atividade]:
    return colaborador.atividades.order_by("id").first()


def gerar_alerta_colaborador(localizacao: Localizacao, colaborador: Colaborador) -> AlertaOperacional:
    atividade = _atividade_principal_colaborador(colaborador)
    atividade_nome = atividade.nome if atividade else "atividade não informada"

    risco = classificar_risco(
        temperatura=float(localizacao.temperatura or 0),
        umidade=int(localizacao.umidade or 0),
        indice_calor=float(localizacao.indice_calor or 0),
        jornada_horas=colaborador.jornada_horas,
        atividade_nome=atividade_nome,
    )

    texto = montar_texto_alerta(colaborador.nome, atividade_nome, risco)

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

    for colaborador in colaboradores:
        atividade = _atividade_principal_colaborador(colaborador)
        atividade_nome = atividade.nome if atividade else "atividade não informada"

        risco = classificar_risco(
            temperatura=float(localizacao.temperatura or 0),
            umidade=int(localizacao.umidade or 0),
            indice_calor=float(localizacao.indice_calor or 0),
            jornada_horas=colaborador.jornada_horas,
            atividade_nome=atividade_nome,
        )

        if maior_risco is None or _peso_nivel(risco.nivel) > _peso_nivel(maior_risco.nivel):
            maior_risco = risco
            atividade_referencia = atividade_nome

    if maior_risco is None:
        return None

    texto = montar_texto_alerta(f"Equipe {equipe.nome}", atividade_referencia, maior_risco)

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
        return []

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

