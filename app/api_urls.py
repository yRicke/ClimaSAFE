from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    AtividadeViewSet,
    AtualizarLocalizacaoAPIView,
    ColaboradorViewSet,
    DashboardAPIView,
    EquipeViewSet,
    FazendaViewSet,
    ProcessarAlertasAPIView,
    ProcessarDadosClimaticosAPIView,
)

router = DefaultRouter()
router.register("fazendas", FazendaViewSet, basename="api-fazendas")
router.register("equipes", EquipeViewSet, basename="api-equipes")
router.register("colaboradores", ColaboradorViewSet, basename="api-colaboradores")
router.register("atividades", AtividadeViewSet, basename="api-atividades")

urlpatterns = [
    path("dashboard/", DashboardAPIView.as_view(), name="api-dashboard"),
    path("localizacao/", AtualizarLocalizacaoAPIView.as_view(), name="api-localizacao"),
    path("processar-clima/", ProcessarDadosClimaticosAPIView.as_view(), name="api-processar-clima"),
    path("processar-alertas/", ProcessarAlertasAPIView.as_view(), name="api-processar-alertas"),
    path("", include(router.urls)),
]

