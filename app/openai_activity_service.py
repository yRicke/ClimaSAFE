from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


logger = logging.getLogger(__name__)

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

ATIVIDADE_INSTRUCTIONS = (
    "Voce recebe uma descricao de atividade rural em portugues do Brasil. "
    "Responda somente com JSON valido, sem markdown e sem texto extra, usando este formato: "
    '{"nome":"<atividade_curta>","intensidade":<1_a_10>}. '
    "O campo nome deve ser curto e objetivo. "
    "A intensidade vai de 1 (leve) a 10 (muito pesada)."
)


def gerar_atividade_por_descricao_openai(descricao: str) -> Optional[dict[str, Any]]:
    if not settings.OPENAI_ALERTS_ENABLED or not settings.OPENAI_API_KEY:
        return None

    descricao = (descricao or "").strip()
    if not descricao:
        return None

    payload = {
        "model": getattr(settings, "OPENAI_ACTIVITY_MODEL", settings.OPENAI_ALERT_MODEL),
        "instructions": ATIVIDADE_INSTRUCTIONS,
        "input": f"Descricao da atividade:\n{descricao}",
        "reasoning": {"effort": settings.OPENAI_ALERT_REASONING_EFFORT},
        "text": {"verbosity": settings.OPENAI_ALERT_TEXT_VERBOSITY},
        "store": False,
    }

    request = Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=settings.OPENAI_ALERT_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detalhes = exc.read().decode("utf-8", errors="ignore")
        logger.warning("Falha HTTP ao gerar atividade via OpenAI: %s", detalhes or exc)
        return None
    except (URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Falha ao gerar atividade via OpenAI: %s", exc)
        return None

    texto = _extrair_output_text(body)
    if not texto:
        logger.warning("Resposta da OpenAI sem texto utilizavel para atividade.")
        return None

    atividade = _normalizar_atividade(texto)
    if not atividade:
        logger.warning("Resposta da OpenAI sem JSON valido para atividade: %s", texto)
        return None

    return atividade


def _extrair_output_text(body: dict[str, Any]) -> str:
    partes: list[str] = []

    for item in body.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                texto = str(content.get("text", "")).strip()
                if texto:
                    partes.append(texto)

    return " ".join(partes).strip()


def _normalizar_atividade(texto: str) -> Optional[dict[str, Any]]:
    bruto = _extrair_json(texto)
    if not bruto:
        return None

    nome = " ".join(str(bruto.get("nome", "")).split()).strip()
    if not nome:
        return None
    if len(nome) > 150:
        nome = nome[:150].rsplit(" ", 1)[0].strip() or nome[:150].strip()

    intensidade_bruta = bruto.get("intensidade")
    try:
        intensidade = int(round(float(intensidade_bruta)))
    except (TypeError, ValueError):
        return None

    intensidade = max(1, min(10, intensidade))
    return {"nome": nome, "intensidade": intensidade}


def _extrair_json(texto: str) -> Optional[dict[str, Any]]:
    texto = texto.strip()
    try:
        bruto = json.loads(texto)
        if isinstance(bruto, dict):
            return bruto
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if not match:
        return None

    try:
        bruto = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None

    if not isinstance(bruto, dict):
        return None
    return bruto
