import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from .forms import AtividadeForm
from .models import Atividade, Colaborador, Fazenda, Localizacao
from .openai_activity_service import gerar_atividade_por_descricao_openai
from .openai_alert_service import gerar_texto_alerta_openai
from .services import processar_alertas_fazenda


class AlertasOpenAITestCase(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username="teste", password="segredo")
        self.fazenda = Fazenda.objects.create(usuario=self.usuario, nome="Fazenda Modelo")
        self.localizacao = Localizacao.objects.create(
            fazenda=self.fazenda,
            latitude="-23.550520",
            longitude="-46.633308",
            horario="08:00",
            endereco_aproximado="Zona rural",
            clima="Sol forte",
            temperatura="34.00",
            umidade=65,
            indice_calor="41.20",
        )
        self.colaborador = Colaborador.objects.create(
            fazenda=self.fazenda,
            nome="João",
            jornada_horas=8,
        )
        Atividade.objects.create(
            colaborador=self.colaborador,
            nome="colheita",
            intensidade=9,
        )

    @patch("app.services.gerar_texto_alerta_openai", return_value="João deve limitar a colheita intensa a 1h seguida e fazer pausas de 5 min a cada 30 min.")
    def test_processar_alertas_usa_texto_da_openai_quando_disponivel(self, mock_openai):
        alertas = processar_alertas_fazenda(self.fazenda)

        self.assertEqual(len(alertas), 1)
        self.assertEqual(
            alertas[0].texto,
            "João deve limitar a colheita intensa a 1h seguida e fazer pausas de 5 min a cada 30 min.",
        )
        contexto = mock_openai.call_args.args[0]
        self.assertEqual(contexto["alvo_nome"], "João")
        self.assertEqual(contexto["atividade_nome"], "colheita")
        self.assertEqual(contexto["nivel_risco"], "critico")
        self.assertEqual(contexto["temperatura_c"], 34.0)

    @patch("app.services.gerar_texto_alerta_openai", return_value=None)
    def test_processar_alertas_faz_fallback_para_texto_padrao(self, _mock_openai):
        alertas = processar_alertas_fazenda(self.fazenda)

        self.assertEqual(len(alertas), 1)
        self.assertEqual(
            alertas[0].texto,
            "João não pode executar 'colheita' (intensidade 9/10) por mais de 1h seguidas. "
            "Sugestão: pausas de 5 min a cada 30 min.",
        )

    @override_settings(
        OPENAI_API_KEY="chave-teste",
        OPENAI_ALERTS_ENABLED=True,
        OPENAI_ALERT_MODEL="gpt-5.4-mini",
        OPENAI_ALERT_REASONING_EFFORT="low",
        OPENAI_ALERT_TEXT_VERBOSITY="low",
        OPENAI_ALERT_TIMEOUT_SECONDS=12.5,
    )
    @patch("app.openai_alert_service.urlopen")
    def test_gerar_texto_alerta_openai_monta_requisicao_e_extrai_texto(self, mock_urlopen):
        resposta_api = {
            "output": [
                {"type": "reasoning", "content": []},
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Equipe Campo Sul deve reduzir a exposição a 2h e manter pausas de 5 min a cada 60 min.",
                        }
                    ],
                },
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(resposta_api).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        texto = gerar_texto_alerta_openai(
            {
                "alvo_nome": "Equipe Campo Sul",
                "atividade_nome": "capina",
                "nivel_risco": "alto",
            }
        )

        self.assertEqual(
            texto,
            "Equipe Campo Sul deve reduzir a exposição a 2h e manter pausas de 5 min a cada 60 min.",
        )
        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "gpt-5.4-mini")
        self.assertEqual(payload["reasoning"]["effort"], "low")
        self.assertEqual(payload["text"]["verbosity"], "low")
        self.assertFalse(payload["store"])

    @override_settings(OPENAI_API_KEY="", OPENAI_ALERTS_ENABLED=True)
    @patch("app.openai_alert_service.urlopen")
    def test_gerar_texto_alerta_openai_retorna_none_sem_chave(self, mock_urlopen):
        texto = gerar_texto_alerta_openai({"alvo_nome": "João"})

        self.assertIsNone(texto)
        mock_urlopen.assert_not_called()


class AtividadeOpenAITestCase(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username="atividade-user", password="segredo")
        self.fazenda = Fazenda.objects.create(usuario=self.usuario, nome="Fazenda Atividade")
        self.colaborador = Colaborador.objects.create(
            fazenda=self.fazenda,
            nome="Carlos",
            jornada_horas=8,
        )

    @patch("app.forms.gerar_atividade_por_descricao_openai")
    def test_form_gera_nome_e_intensidade_com_ia(self, mock_gerar):
        mock_gerar.return_value = {"nome": "capina manual", "intensidade": 8}
        form = AtividadeForm(
            data={
                "colaborador": self.colaborador.id,
                "descricao": "Capina manual com enxada durante toda a manha sob sol forte.",
                "nome": "",
                "intensidade": "",
            },
            user=self.usuario,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertEqual(form.cleaned_data["nome"], "capina manual")
        self.assertEqual(form.cleaned_data["intensidade"], 8)

    @patch("app.forms.gerar_atividade_por_descricao_openai", return_value=None)
    def test_form_faz_fallback_manual_quando_ia_nao_retorna(self, _mock_gerar):
        form = AtividadeForm(
            data={
                "colaborador": self.colaborador.id,
                "descricao": "Operacao com pulverizador costal em ritmo constante.",
                "nome": "pulverizacao",
                "intensidade": 6,
            },
            user=self.usuario,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertEqual(form.cleaned_data["nome"], "pulverizacao")
        self.assertEqual(form.cleaned_data["intensidade"], 6)

    @override_settings(
        OPENAI_API_KEY="chave-teste",
        OPENAI_ALERTS_ENABLED=True,
        OPENAI_ALERT_MODEL="gpt-5.4-mini",
        OPENAI_ACTIVITY_MODEL="gpt-5.4-mini",
        OPENAI_ALERT_REASONING_EFFORT="low",
        OPENAI_ALERT_TEXT_VERBOSITY="low",
        OPENAI_ALERT_TIMEOUT_SECONDS=12.5,
    )
    @patch("app.openai_activity_service.urlopen")
    def test_gerar_atividade_por_descricao_openai_extrai_json(self, mock_urlopen):
        resposta_api = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": '{"nome":"plantio de mudas","intensidade":7}'}
                    ],
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(resposta_api).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        atividade = gerar_atividade_por_descricao_openai(
            "Plantio de mudas com abertura de covas, transporte de caixas e exposicao ao sol."
        )

        self.assertEqual(atividade, {"nome": "plantio de mudas", "intensidade": 7})
        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "gpt-5.4-mini")
        self.assertFalse(payload["store"])

    @override_settings(OPENAI_API_KEY="", OPENAI_ALERTS_ENABLED=True)
    @patch("app.openai_activity_service.urlopen")
    def test_gerar_atividade_por_descricao_openai_retorna_none_sem_chave(self, mock_urlopen):
        atividade = gerar_atividade_por_descricao_openai("Descricao detalhada")
        self.assertIsNone(atividade)
        mock_urlopen.assert_not_called()
