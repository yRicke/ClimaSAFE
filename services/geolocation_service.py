import json
import os
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


NOMINATIM_REVERSE_URL = os.getenv(
    "NOMINATIM_REVERSE_URL", "https://nominatim.openstreetmap.org/reverse"
)


@dataclass
class GeolocationResult:
    latitude: float
    longitude: float
    address: str = ""


def validar_coordenadas(latitude: float, longitude: float) -> tuple[float, float]:
    lat = float(latitude)
    lon = float(longitude)

    if lat < -90 or lat > 90:
        raise ValueError("Latitude fora do intervalo permitido (-90 a 90).")
    if lon < -180 or lon > 180:
        raise ValueError("Longitude fora do intervalo permitido (-180 a 180).")

    return lat, lon


def reverse_geocode(latitude: float, longitude: float) -> str:
    """
    Busca endereço aproximado para coordenadas.

    Para trocar o provider futuramente:
    - substitua esta função por integração com outro endpoint (Mapbox, LocationIQ, etc.);
    - mantenha a mesma assinatura para não afetar views/JS.
    """
    params = urlencode(
        {
            "format": "jsonv2",
            "lat": latitude,
            "lon": longitude,
            "addressdetails": 1,
        }
    )
    url = f"{NOMINATIM_REVERSE_URL}?{params}"

    request = Request(
        url,
        headers={
            "User-Agent": "ClimaSAFE/1.0 (contato-local)",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except URLError:
        return ""

    return payload.get("display_name", "")


def selecionar_localizacao(latitude: float, longitude: float, buscar_endereco: bool = True) -> GeolocationResult:
    lat, lon = validar_coordenadas(latitude, longitude)
    address = reverse_geocode(lat, lon) if buscar_endereco else ""
    return GeolocationResult(latitude=lat, longitude=lon, address=address)


# Integração futura:
# - Open-Meteo: usar latitude/longitude retornadas por selecionar_localizacao.
# - OpenTopoData: consultar altitude com essas coordenadas.
# - Persistência em models: salvar lat/lon no model Localizacao via service de domínio.
# - Geometrias (polígonos): expandir o payload para lista de pontos e manter validação centralizada aqui.
