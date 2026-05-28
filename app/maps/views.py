import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from services.geolocation_service import selecionar_localizacao


@require_POST
@login_required
def select_location_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"success": False, "error": "Payload JSON inválido."},
            status=400,
        )

    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    include_address = bool(payload.get("include_address", True))

    if latitude is None or longitude is None:
        return JsonResponse(
            {"success": False, "error": "Campos obrigatórios: latitude e longitude."},
            status=400,
        )

    try:
        result = selecionar_localizacao(
            latitude=latitude,
            longitude=longitude,
            buscar_endereco=include_address,
        )
    except ValueError as exc:
        return JsonResponse(
            {"success": False, "error": str(exc)},
            status=400,
        )
    except Exception:
        return JsonResponse(
            {"success": False, "error": "Falha interna ao processar localização."},
            status=500,
        )

    return JsonResponse(
        {
            "success": True,
            "latitude": result.latitude,
            "longitude": result.longitude,
            "address": result.address,
        },
        status=200,
    )
