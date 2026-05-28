from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("dashboard/salvar-localizacao/", views.salvar_localizacao, name="salvar_localizacao"),
    path(
        "dashboard/processar-dados-climaticos/",
        views.processar_dados_climaticos,
        name="processar_dados_climaticos",
    ),
    path("dashboard/processar-alertas/", views.processar_alertas, name="processar_alertas"),
    path("fazendas/", views.FazendaListView.as_view(), name="fazenda_list"),
    path("fazendas/nova/", views.FazendaCreateView.as_view(), name="fazenda_create"),
    path("fazendas/<int:pk>/editar/", views.FazendaUpdateView.as_view(), name="fazenda_update"),
    path("fazendas/<int:pk>/excluir/", views.fazenda_delete, name="fazenda_delete"),
    path("equipes/", views.EquipeListView.as_view(), name="equipe_list"),
    path("equipes/nova/", views.EquipeCreateView.as_view(), name="equipe_create"),
    path("equipes/<int:pk>/editar/", views.EquipeUpdateView.as_view(), name="equipe_update"),
    path("equipes/<int:pk>/excluir/", views.equipe_delete, name="equipe_delete"),
    path("colaboradores/", views.ColaboradorListView.as_view(), name="colaborador_list"),
    path("colaboradores/novo/", views.ColaboradorCreateView.as_view(), name="colaborador_create"),
    path("colaboradores/<int:pk>/editar/", views.ColaboradorUpdateView.as_view(), name="colaborador_update"),
    path("colaboradores/<int:pk>/excluir/", views.colaborador_delete, name="colaborador_delete"),
    path("atividades/", views.AtividadeListView.as_view(), name="atividade_list"),
    path("atividades/nova/", views.AtividadeCreateView.as_view(), name="atividade_create"),
    path("atividades/<int:pk>/editar/", views.AtividadeUpdateView.as_view(), name="atividade_update"),
    path("atividades/<int:pk>/excluir/", views.atividade_delete, name="atividade_delete"),
]

