from rest_framework import serializers

from .models import AlertaOperacional, Atividade, Colaborador, Equipe, Fazenda, Localizacao
from .openai_activity_service import gerar_atividade_por_descricao_openai


class FazendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fazenda
        fields = ["id", "nome"]


class EquipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipe
        fields = ["id", "fazenda", "nome"]

    def validate_fazenda(self, fazenda):
        request = self.context["request"]
        if fazenda.usuario_id != request.user.id:
            raise serializers.ValidationError("Fazenda inválida para o usuário logado.")
        return fazenda


class ColaboradorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Colaborador
        fields = ["id", "fazenda", "equipe", "nome", "jornada_horas"]

    def validate(self, attrs):
        request = self.context["request"]

        fazenda = attrs.get("fazenda", getattr(self.instance, "fazenda", None))
        equipe = attrs.get("equipe", getattr(self.instance, "equipe", None))

        if fazenda and fazenda.usuario_id != request.user.id:
            raise serializers.ValidationError({"fazenda": "Fazenda inválida para o usuário logado."})

        if equipe:
            if equipe.fazenda.usuario_id != request.user.id:
                raise serializers.ValidationError({"equipe": "Equipe inválida para o usuário logado."})
            if fazenda and equipe.fazenda_id != fazenda.id:
                raise serializers.ValidationError({"equipe": "Equipe deve pertencer à mesma fazenda."})

        return attrs


class AtividadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Atividade
        fields = ["id", "colaborador", "descricao", "nome", "intensidade"]

    def validate_colaborador(self, colaborador):
        request = self.context["request"]
        if colaborador.fazenda.usuario_id != request.user.id:
            raise serializers.ValidationError("Colaborador inválido para o usuário logado.")
        return colaborador

    def validate(self, attrs):
        attrs = super().validate(attrs)
        descricao = (attrs.get("descricao") or getattr(self.instance, "descricao", "") or "").strip()

        if not descricao:
            raise serializers.ValidationError(
                {"descricao": "Descreva com clareza como essa atividade e realizada."}
            )

        atividade_ia = gerar_atividade_por_descricao_openai(descricao)
        if atividade_ia:
            attrs["nome"] = atividade_ia["nome"]
            attrs["intensidade"] = atividade_ia["intensidade"]
            return attrs

        nome_existente = getattr(self.instance, "nome", "")
        intensidade_existente = getattr(self.instance, "intensidade", None)

        if not attrs.get("nome") and not nome_existente:
            raise serializers.ValidationError(
                {"nome": "Nao foi possivel gerar automaticamente. Informe o nome da atividade."}
            )
        if attrs.get("intensidade") in (None, "") and intensidade_existente in (None, ""):
            raise serializers.ValidationError(
                {"intensidade": "Nao foi possivel gerar automaticamente. Informe a intensidade."}
            )

        return attrs


class LocalizacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Localizacao
        fields = [
            "id",
            "fazenda",
            "latitude",
            "longitude",
            "horario",
            "endereco_aproximado",
            "clima",
            "temperatura",
            "umidade",
            "indice_calor",
            "atualizado_em",
        ]
        read_only_fields = ["clima", "temperatura", "umidade", "indice_calor", "atualizado_em"]


class AlertaOperacionalSerializer(serializers.ModelSerializer):
    colaborador_nome = serializers.CharField(source="colaborador.nome", read_only=True)
    equipe_nome = serializers.CharField(source="equipe.nome", read_only=True)

    class Meta:
        model = AlertaOperacional
        fields = [
            "id",
            "localizacao",
            "colaborador",
            "colaborador_nome",
            "equipe",
            "equipe_nome",
            "texto",
            "nivel",
            "criado_em",
        ]

