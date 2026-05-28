from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .forms import AtividadeForm, ColaboradorForm, EquipeForm, FazendaForm
from .models import AlertaOperacional, Atividade, Colaborador, Equipe, Fazenda, Localizacao
from .services import (
    processar_alertas_fazenda,
    processar_dados_climaticos_fazenda,
    salvar_localizacao_fazenda,
)


class UserFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


@login_required
def index(request):
    return redirect("dashboard")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    @staticmethod
    def _format_coord(value):
        if value is None:
            return ""
        return f"{value:.6f}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        fazendas = Fazenda.objects.filter(usuario=self.request.user)
        fazenda_id = self.request.GET.get("fazenda") or self.request.session.get("fazenda_ativa_id")

        fazenda_ativa = fazendas.filter(id=fazenda_id).first() if fazenda_id else fazendas.first()

        if fazenda_ativa:
            self.request.session["fazenda_ativa_id"] = fazenda_ativa.id

        localizacao = Localizacao.objects.filter(fazenda=fazenda_ativa).first() if fazenda_ativa else None
        alertas = (
            AlertaOperacional.objects.filter(localizacao=localizacao)
            if localizacao
            else AlertaOperacional.objects.none()
        )

        latitude_value = self._format_coord(localizacao.latitude) if localizacao else ""
        longitude_value = self._format_coord(localizacao.longitude) if localizacao else ""

        context.update(
            {
                "fazendas": fazendas,
                "fazenda_ativa": fazenda_ativa,
                "localizacao": localizacao,
                "latitude_value": latitude_value,
                "longitude_value": longitude_value,
                "alertas": alertas,
                "map_tile_url": getattr(
                    settings, "MAP_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                ),
            }
        )
        return context


@require_POST
@login_required
def salvar_localizacao(request):
    fazenda_id = request.POST.get("fazenda")
    latitude = request.POST.get("latitude")
    longitude = request.POST.get("longitude")
    horario = request.POST.get("horario")
    endereco_aproximado = request.POST.get("endereco_aproximado", "")

    fazenda = get_object_or_404(Fazenda, id=fazenda_id, usuario=request.user)

    try:
        salvar_localizacao_fazenda(
            fazenda=fazenda,
            latitude=float(latitude),
            longitude=float(longitude),
            horario=str(horario),
            endereco_aproximado=endereco_aproximado,
        )
        messages.success(request, "Localização salva. Agora clique em 'Processar dados climáticos'.")
    except (TypeError, ValueError) as exc:
        messages.error(request, f"Erro ao salvar localização: {exc}")

    return redirect(f"{reverse_lazy('dashboard')}?fazenda={fazenda.id}")


@require_POST
@login_required
def processar_dados_climaticos(request):
    fazenda_id = request.POST.get("fazenda")
    fazenda = get_object_or_404(Fazenda, id=fazenda_id, usuario=request.user)

    try:
        processar_dados_climaticos_fazenda(fazenda)
        messages.success(request, "Dados climáticos processados com sucesso.")
    except ValueError as exc:
        messages.error(request, str(exc))
    except RuntimeError as exc:
        messages.error(request, str(exc))

    return redirect(f"{reverse_lazy('dashboard')}?fazenda={fazenda.id}")


@require_POST
@login_required
def processar_alertas(request):
    fazenda_id = request.POST.get("fazenda")
    fazenda = get_object_or_404(Fazenda, id=fazenda_id, usuario=request.user)

    try:
        alertas = processar_alertas_fazenda(fazenda)
        messages.success(request, f"{len(alertas)} alertas processados.")
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect(f"{reverse_lazy('dashboard')}?fazenda={fazenda.id}")


class FazendaListView(LoginRequiredMixin, ListView):
    model = Fazenda
    template_name = "fazenda_list.html"
    context_object_name = "fazendas"

    def get_queryset(self):
        return Fazenda.objects.filter(usuario=self.request.user)


class FazendaCreateView(LoginRequiredMixin, CreateView):
    model = Fazenda
    form_class = FazendaForm
    template_name = "fazenda_form.html"
    success_url = reverse_lazy("fazenda_list")

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class FazendaUpdateView(LoginRequiredMixin, UpdateView):
    model = Fazenda
    form_class = FazendaForm
    template_name = "fazenda_form.html"
    success_url = reverse_lazy("fazenda_list")

    def get_queryset(self):
        return Fazenda.objects.filter(usuario=self.request.user)


@require_POST
@login_required
def fazenda_delete(request, pk):
    fazenda = get_object_or_404(Fazenda, pk=pk, usuario=request.user)
    fazenda.delete()
    messages.success(request, "Fazenda removida.")
    return redirect("fazenda_list")


class EquipeListView(LoginRequiredMixin, ListView):
    model = Equipe
    template_name = "equipe_list.html"
    context_object_name = "equipes"

    def get_queryset(self):
        return Equipe.objects.filter(fazenda__usuario=self.request.user).select_related("fazenda")


class EquipeCreateView(LoginRequiredMixin, UserFormKwargsMixin, CreateView):
    model = Equipe
    form_class = EquipeForm
    template_name = "equipe_form.html"
    success_url = reverse_lazy("equipe_list")


class EquipeUpdateView(LoginRequiredMixin, UserFormKwargsMixin, UpdateView):
    model = Equipe
    form_class = EquipeForm
    template_name = "equipe_form.html"
    success_url = reverse_lazy("equipe_list")

    def get_queryset(self):
        return Equipe.objects.filter(fazenda__usuario=self.request.user)


@require_POST
@login_required
def equipe_delete(request, pk):
    equipe = get_object_or_404(Equipe, pk=pk, fazenda__usuario=request.user)
    equipe.delete()
    messages.success(request, "Equipe removida.")
    return redirect("equipe_list")


class ColaboradorListView(LoginRequiredMixin, ListView):
    model = Colaborador
    template_name = "colaborador_list.html"
    context_object_name = "colaboradores"

    def get_queryset(self):
        return Colaborador.objects.filter(fazenda__usuario=self.request.user).select_related("fazenda", "equipe")


class ColaboradorCreateView(LoginRequiredMixin, UserFormKwargsMixin, CreateView):
    model = Colaborador
    form_class = ColaboradorForm
    template_name = "colaborador_form.html"
    success_url = reverse_lazy("colaborador_list")


class ColaboradorUpdateView(LoginRequiredMixin, UserFormKwargsMixin, UpdateView):
    model = Colaborador
    form_class = ColaboradorForm
    template_name = "colaborador_form.html"
    success_url = reverse_lazy("colaborador_list")

    def get_queryset(self):
        return Colaborador.objects.filter(fazenda__usuario=self.request.user)


@require_POST
@login_required
def colaborador_delete(request, pk):
    colaborador = get_object_or_404(Colaborador, pk=pk, fazenda__usuario=request.user)
    colaborador.delete()
    messages.success(request, "Colaborador removido.")
    return redirect("colaborador_list")


class AtividadeListView(LoginRequiredMixin, ListView):
    model = Atividade
    template_name = "atividade_list.html"
    context_object_name = "atividades"

    def get_queryset(self):
        return Atividade.objects.filter(colaborador__fazenda__usuario=self.request.user).select_related(
            "colaborador"
        )


class AtividadeCreateView(LoginRequiredMixin, UserFormKwargsMixin, CreateView):
    model = Atividade
    form_class = AtividadeForm
    template_name = "atividade_form.html"
    success_url = reverse_lazy("atividade_list")


class AtividadeUpdateView(LoginRequiredMixin, UserFormKwargsMixin, UpdateView):
    model = Atividade
    form_class = AtividadeForm
    template_name = "atividade_form.html"
    success_url = reverse_lazy("atividade_list")

    def get_queryset(self):
        return Atividade.objects.filter(colaborador__fazenda__usuario=self.request.user)


@require_POST
@login_required
def atividade_delete(request, pk):
    atividade = get_object_or_404(Atividade, pk=pk, colaborador__fazenda__usuario=request.user)
    atividade.delete()
    messages.success(request, "Atividade removida.")
    return redirect("atividade_list")
