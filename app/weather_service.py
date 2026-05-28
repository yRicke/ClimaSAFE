import json
from dataclasses import dataclass
from decimal import Decimal
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


WEATHER_CODE_MAP = {
    0: "Céu limpo",
    1: "Predominantemente limpo",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Névoa",
    48: "Névoa com geada",
    51: "Garoa leve",
    53: "Garoa moderada",
    55: "Garoa intensa",
    61: "Chuva leve",
    63: "Chuva moderada",
    65: "Chuva forte",
    71: "Neve leve",
    73: "Neve moderada",
    75: "Neve forte",
    80: "Pancadas de chuva leves",
    81: "Pancadas de chuva moderadas",
    82: "Pancadas de chuva fortes",
    95: "Trovoada",
    96: "Trovoada com granizo leve",
    99: "Trovoada com granizo forte",
}


@dataclass
class DadosClimaticos:
    clima: str
    temperatura: Decimal
    umidade: int
    indice_calor: Decimal


def calcular_indice_calor(temperatura: float, umidade: float) -> float:
    """
    Aproximação prática do Heat Index com base na fórmula NOAA
    (conversão Celsius/Fahrenheit).
    """
    temperatura_f = (temperatura * 9 / 5) + 32
    hi_f = (
        -42.379
        + (2.04901523 * temperatura_f)
        + (10.14333127 * umidade)
        - (0.22475541 * temperatura_f * umidade)
        - (0.00683783 * temperatura_f * temperatura_f)
        - (0.05481717 * umidade * umidade)
        + (0.00122874 * temperatura_f * temperatura_f * umidade)
        + (0.00085282 * temperatura_f * umidade * umidade)
        - (0.00000199 * temperatura_f * temperatura_f * umidade * umidade)
    )

    if temperatura_f < 80:
        hi_f = temperatura_f

    return round((hi_f - 32) * 5 / 9, 2)


def normalizar_resposta_clima(dados_api: dict) -> DadosClimaticos:
    current = dados_api.get("current", {})

    temperatura = float(current.get("temperature_2m", 0.0))
    umidade = int(current.get("relative_humidity_2m", 0))
    weather_code = int(current.get("weather_code", -1))

    indice_calor = calcular_indice_calor(temperatura, umidade)
    clima = WEATHER_CODE_MAP.get(weather_code, "Condição não identificada")

    return DadosClimaticos(
        clima=clima,
        temperatura=Decimal(str(round(temperatura, 2))),
        umidade=umidade,
        indice_calor=Decimal(str(indice_calor)),
    )


def buscar_dados_climaticos(latitude: float, longitude: float) -> DadosClimaticos:
    params = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,weather_code",
            "timezone": "auto",
            "forecast_days": 1,
        }
    )
    url = f"{OPEN_METEO_URL}?{params}"

    try:
        with urlopen(url, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError("Falha ao consultar dados climáticos") from exc

    return normalizar_resposta_clima(payload)

