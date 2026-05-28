from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AlertaOperacional, Atividade, Colaborador, Equipe, Fazenda, Localizacao
from .serializers import (
    AlertaOperacionalSerializer,
    AtividadeSerializer,
    ColaboradorSerializer,
    EquipeSerializer,
    FazendaSerializer,
    LocalizacaoSerializer,
)
from .services import atualizar_localizacao_fazenda, processar_alertas_fazenda


class FazendaViewSet(viewsets.ModelViewSet):
    serializer_class = FazendaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Fazenda.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


class EquipeViewSet(viewsets.ModelViewSet):
    serializer_class = EquipeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Equipe.objects.filter(fazenda__usuario=self.request.user)


class ColaboradorViewSet(viewsets.ModelViewSet):
    serializer_class = ColaboradorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Colaborador.objects.filter(fazenda__usuario=self.request.user)


class AtividadeViewSet(viewsets.ModelViewSet):
    serializer_class = AtividadeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Atividade.objects.filter(colaborador__fazenda__usuario=self.request.user)


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        fazenda_id = request.query_params.get("fazenda")
        fazendas = Fazenda.objects.filter(usuario=request.user)

        if fazenda_id:
            fazenda = fazendas.filter(id=fazenda_id).first()
        else:
            fazenda = fazendas.first()

        if not fazenda:
            return Response(
                {
                    "fazenda_ativa": None,
                    "localizacao": None,
                    "alertas": [],
                }
            )

        localizacao = Localizacao.objects.filter(fazenda=fazenda).first()
        alertas = AlertaOperacional.objects.filter(localizacao=localizacao) if localizacao else []

        return Response(
            {
                "fazenda_ativa": FazendaSerializer(fazenda).data,
                "localizacao": LocalizacaoSerializer(localizacao).data if localizacao else None,
                "alertas": AlertaOperacionalSerializer(alertas, many=True).data,
            }
        )


class AtualizarLocalizacaoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        fazenda_id = request.data.get("fazenda")
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        horario = request.data.get("horario")

        if not all([fazenda_id, latitude, longitude, horario]):
            return Response(
                {"detail": "Campos obrigatórios: fazenda, latitude, longitude, horario."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fazenda = Fazenda.objects.filter(id=fazenda_id, usuario=request.user).first()
        if not fazenda:
            return Response({"detail": "Fazenda não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            localizacao = atualizar_localizacao_fazenda(
                fazenda=fazenda,
                latitude=float(latitude),
                longitude=float(longitude),
                horario=str(horario),
            )
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(LocalizacaoSerializer(localizacao).data, status=status.HTTP_200_OK)


class ProcessarAlertasAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        fazenda_id = request.data.get("fazenda")
        if not fazenda_id:
            return Response(
                {"detail": "Campo obrigatório: fazenda."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fazenda = Fazenda.objects.filter(id=fazenda_id, usuario=request.user).first()
        if not fazenda:
            return Response({"detail": "Fazenda não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        alertas = processar_alertas_fazenda(fazenda)
        return Response(AlertaOperacionalSerializer(alertas, many=True).data, status=status.HTTP_200_OK)

