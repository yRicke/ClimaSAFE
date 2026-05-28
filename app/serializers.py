from rest_framework import serializers

from .models import AlertaOperacional, Atividade, Colaborador, Equipe, Fazenda, Localizacao


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
        fields = ["id", "colaborador", "nome"]

    def validate_colaborador(self, colaborador):
        request = self.context["request"]
        if colaborador.fazenda.usuario_id != request.user.id:
            raise serializers.ValidationError("Colaborador inválido para o usuário logado.")
        return colaborador


class LocalizacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Localizacao
        fields = [
            "id",
            "fazenda",
            "latitude",
            "longitude",
            "horario",
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

