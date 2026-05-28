from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Fazenda(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fazendas")
    nome = models.CharField(max_length=120)

    class Meta:
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class Equipe(models.Model):
    fazenda = models.ForeignKey(Fazenda, on_delete=models.CASCADE, related_name="equipes")
    nome = models.CharField(max_length=120)

    class Meta:
        ordering = ["nome"]
        unique_together = ("fazenda", "nome")

    def __str__(self) -> str:
        return f"{self.nome} ({self.fazenda.nome})"


class Colaborador(models.Model):
    fazenda = models.ForeignKey(Fazenda, on_delete=models.CASCADE, related_name="colaboradores")
    equipe = models.ForeignKey(
        Equipe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="colaboradores",
    )
    nome = models.CharField(max_length=120)
    jornada_horas = models.PositiveSmallIntegerField(
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(24)],
    )

    class Meta:
        ordering = ["nome"]
        unique_together = ("fazenda", "nome")

    def clean(self) -> None:
        if self.equipe and self.equipe.fazenda_id != self.fazenda_id:
            raise ValidationError("A equipe do colaborador deve pertencer a mesma fazenda.")

    def __str__(self) -> str:
        return self.nome


class Atividade(models.Model):
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name="atividades")
    nome = models.CharField(max_length=150)
    intensidade = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Intensidade da atividade de 1 (leve) a 10 (muito pesada).",
    )

    class Meta:
        ordering = ["nome"]

    def __str__(self) -> str:
        return f"{self.nome} (intensidade {self.intensidade}/10) - {self.colaborador.nome}"


class Localizacao(models.Model):
    fazenda = models.OneToOneField(Fazenda, on_delete=models.CASCADE, related_name="localizacao_ativa")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    horario = models.CharField(max_length=80)
    endereco_aproximado = models.CharField(max_length=255, blank=True)
    clima = models.CharField(max_length=80, blank=True)
    temperatura = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    umidade = models.PositiveSmallIntegerField(null=True, blank=True)
    indice_calor = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Localização"
        verbose_name_plural = "Localizações"

    def __str__(self) -> str:
        return f"{self.fazenda.nome} ({self.latitude}, {self.longitude})"


class AlertaOperacional(models.Model):
    class Niveis(models.TextChoices):
        BAIXO = "baixo", "Baixo"
        ATENCAO = "atencao", "Atenção"
        ALTO = "alto", "Alto"
        CRITICO = "critico", "Crítico"

    localizacao = models.ForeignKey(Localizacao, on_delete=models.CASCADE, related_name="alertas")
    colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alertas",
    )
    equipe = models.ForeignKey(
        Equipe,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alertas",
    )
    texto = models.TextField()
    nivel = models.CharField(max_length=10, choices=Niveis.choices)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def clean(self) -> None:
        if self.colaborador and self.equipe:
            raise ValidationError("Alerta não pode estar vinculado a equipe e colaborador ao mesmo tempo.")
        if not self.colaborador and not self.equipe:
            raise ValidationError("Alerta deve ser vinculado a uma equipe ou colaborador.")

    def __str__(self) -> str:
        return f"{self.get_nivel_display()} - {self.texto[:50]}"

