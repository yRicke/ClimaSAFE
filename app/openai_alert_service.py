from __future__ import annotations

import json
import logging
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


logger = logging.getLogger(__name__)

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

ALERTA_INSTRUCTIONS = (
    "Você gera alertas operacionais curtos em português do Brasil para trabalho rural. "
    "Mantenha o mesmo sentido técnico do contexto, mas escreva de forma natural, direta e variada. "
    "O alerta deve citar o alvo, a atividade, a intensidade, o limite de exposição e a frequência de pausas. "
    "Use no máximo 2 frases curtas, sem título, sem listas, sem markdown, sem aspas e sem inventar dados. "
    "O texto precisa continuar objetivo e acionável."
)


def gerar_texto_alerta_openai(contexto: dict[str, Any]) -> Optional[str]:
    if not settings.OPENAI_ALERTS_ENABLED or not settings.OPENAI_API_KEY:
        return None

    payload = {
        "model": settings.OPENAI_ALERT_MODEL,
        "instructions": ALERTA_INSTRUCTIONS,
        "input": (
            "Gere somente o texto final do alerta operacional com base neste contexto JSON:\n"
            f"{json.dumps(contexto, ensure_ascii=False)}"
        ),
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
        logger.warning("Falha HTTP ao gerar alerta via OpenAI: %s", detalhes or exc)
        return None
    except (URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Falha ao gerar alerta via OpenAI: %s", exc)
        return None

    texto = _extrair_output_text(body)
    if not texto:
        logger.warning("Resposta da OpenAI sem texto utilizável para alerta.")
        return None

    return _normalizar_texto_alerta(texto)


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


def _normalizar_texto_alerta(texto: str) -> str:
    texto = " ".join(texto.split()).strip().strip('"').strip("'")
    if len(texto) <= 240:
        return texto

    texto_cortado = texto[:240].rsplit(" ", 1)[0].strip()
    return f"{texto_cortado}..."
