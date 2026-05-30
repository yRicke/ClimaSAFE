from django import forms

from .models import Atividade, Colaborador, Equipe, Fazenda
from .openai_activity_service import gerar_atividade_por_descricao_openai


class FazendaForm(forms.ModelForm):
    class Meta:
        model = Fazenda
        fields = ["nome"]


class EquipeForm(forms.ModelForm):
    class Meta:
        model = Equipe
        fields = ["fazenda", "nome"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["fazenda"].queryset = Fazenda.objects.filter(usuario=user)


class ColaboradorForm(forms.ModelForm):
    class Meta:
        model = Colaborador
        fields = ["fazenda", "equipe", "nome", "jornada_horas"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["equipe"].required = False

        if user is not None:
            fazendas = Fazenda.objects.filter(usuario=user)
            equipes = Equipe.objects.filter(fazenda__usuario=user)
            self.fields["fazenda"].queryset = fazendas
            self.fields["equipe"].queryset = equipes

    def clean(self):
        cleaned_data = super().clean()
        fazenda = cleaned_data.get("fazenda")
        equipe = cleaned_data.get("equipe")

        if equipe and fazenda and equipe.fazenda_id != fazenda.id:
            self.add_error("equipe", "A equipe precisa ser da mesma fazenda do colaborador.")

        return cleaned_data


class AtividadeForm(forms.ModelForm):
    class Meta:
        model = Atividade
        fields = ["colaborador", "descricao", "nome", "intensidade"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["colaborador"].queryset = Colaborador.objects.filter(
                fazenda__usuario=user
            )
        self.fields["descricao"].label = "Descricao detalhada da atividade"
        self.fields["descricao"].widget.attrs.update(
            {
                "rows": 5,
                "placeholder": (
                    "Explique claramente como a atividade e feita, esforco fisico, "
                    "ferramentas usadas, ritmo e exposicao ao sol."
                ),
            }
        )
        self.fields["descricao"].required = True
        self.fields["nome"].required = False
        self.fields["intensidade"].required = False

    def clean(self):
        cleaned_data = super().clean()
        descricao = (cleaned_data.get("descricao") or "").strip()
        nome_manual = cleaned_data.get("nome")
        intensidade_manual = cleaned_data.get("intensidade")

        if not descricao:
            self.add_error("descricao", "Descreva com clareza como essa atividade e realizada.")
            return cleaned_data

        atividade_ia = gerar_atividade_por_descricao_openai(descricao)
        self.atividade_gerada_ia = atividade_ia

        if atividade_ia:
            cleaned_data["nome"] = atividade_ia["nome"]
            cleaned_data["intensidade"] = atividade_ia["intensidade"]
            return cleaned_data

        if not nome_manual:
            self.add_error(
                "nome",
                "Nao foi possivel gerar automaticamente. Informe o nome da atividade manualmente.",
            )
        if intensidade_manual in (None, ""):
            self.add_error(
                "intensidade",
                "Nao foi possivel gerar automaticamente. Informe a intensidade manualmente.",
            )

        return cleaned_data

