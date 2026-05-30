from django.contrib import admin

from .models import AlertaOperacional, Atividade, Colaborador, Equipe, Fazenda, Localizacao


@admin.register(Fazenda)
class FazendaAdmin(admin.ModelAdmin):
    list_display = ("nome", "usuario")
    search_fields = ("nome", "usuario__username")


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ("nome", "fazenda")
    search_fields = ("nome", "fazenda__nome")
    list_filter = ("fazenda",)


@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ("nome", "fazenda", "equipe", "jornada_horas")
    search_fields = ("nome",)
    list_filter = ("fazenda", "equipe")


@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    list_display = ("nome", "intensidade", "colaborador", "descricao")
    search_fields = ("nome", "descricao", "colaborador__nome")


@admin.register(Localizacao)
class LocalizacaoAdmin(admin.ModelAdmin):
    list_display = (
        "fazenda",
        "latitude",
        "longitude",
        "horario",
        "endereco_aproximado",
        "temperatura",
        "umidade",
        "indice_calor",
        "atualizado_em",
    )
    list_filter = ("fazenda",)


@admin.register(AlertaOperacional)
class AlertaOperacionalAdmin(admin.ModelAdmin):
    list_display = ("nivel", "localizacao", "equipe", "colaborador", "criado_em")
    list_filter = ("nivel", "criado_em")
    search_fields = ("texto",)

