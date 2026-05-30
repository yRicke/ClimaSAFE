# ClimaSAFE

Sistema web em Django para gerenciamento de fazendas, equipes, colaboradores, atividades e alertas operacionais com base em clima e índice de calor.

## Requisitos

- Python 3.13+
- `pip`
- Windows PowerShell, Prompt de Comando ou terminal equivalente

## 1. Clonar o projeto

```powershell
git clone <URL_DO_REPOSITORIO>
cd ClimaSAFE
```

Se você já está com o projeto baixado, basta entrar na pasta:

```powershell
cd C:\caminho\para\ClimaSAFE
```

## 2. Criar a virtualenv

```powershell
python -m venv venv
```

## 3. Ativar a virtualenv

No PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

No Prompt de Comando (`cmd`):

```bat
venv\Scripts\activate.bat
```

Se o PowerShell bloquear a ativação por política de execução, rode:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Depois ative novamente:

```powershell
.\venv\Scripts\Activate.ps1
```

## 4. Instalar as dependências

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 5. Criar o arquivo `.env`

Copie o arquivo base:

```powershell
Copy-Item base_env.txt .env
```

Edite o `.env` e preencha pelo menos:

```env
DJANGO_SECRET_KEY=sua-chave-secreta
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_LANGUAGE_CODE=pt-br
DJANGO_TIME_ZONE=America/Sao_Paulo
MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
NOMINATIM_REVERSE_URL=https://nominatim.openstreetmap.org/reverse
OPENAI_API_KEY=
OPENAI_ALERTS_ENABLED=True
OPENAI_ALERT_MODEL=gpt-5.4-mini
OPENAI_ACTIVITY_MODEL=gpt-5.4-mini
OPENAI_ALERT_REASONING_EFFORT=low
OPENAI_ALERT_TEXT_VERBOSITY=low
OPENAI_ALERT_TIMEOUT_SECONDS=20
```

Notas:

- `OPENAI_API_KEY` é opcional. Se ficar vazio, o sistema continua funcionando e usa o texto padrão dos alertas.
- `OPENAI_ALERT_MODEL=gpt-5.4-mini` é o padrão recomendado para texto de alertas.
- `OPENAI_ACTIVITY_MODEL=gpt-5.4-mini` é usado para gerar nome/intensidade da atividade a partir da descrição.

## 6. Aplicar as migrações

```powershell
python manage.py migrate
```

## 7. Criar um usuário administrador

Como o sistema usa login do Django, crie um superusuário:

```powershell
python manage.py createsuperuser
```

Preencha:

- nome de usuário
- e-mail opcional
- senha

## 8. Subir o servidor

```powershell
python manage.py runserver
```

O sistema ficará disponível em:

- `http://127.0.0.1:8000/`

## 9. Fazer login

Abra no navegador:

- `http://127.0.0.1:8000/accounts/login/`

Ou simplesmente:

- `http://127.0.0.1:8000/`

Você será redirecionado para o login e depois para o dashboard.

## Fluxo básico de uso

1. Criar uma fazenda
2. Cadastrar equipes e colaboradores
3. Cadastrar atividades com uma descrição clara (a IA sugere nome e intensidade)
4. Salvar a localização da fazenda no dashboard
5. Processar os dados climáticos
6. Processar os alertas operacionais

## Comandos úteis

Verificar a configuração do Django:

```powershell
python manage.py check
```

Rodar os testes:

```powershell
python manage.py test
```

Desativar a virtualenv:

```powershell
deactivate
```

## Solução de problemas

### `ModuleNotFoundError`

Se aparecer erro de módulo não encontrado, confirme que:

1. A virtualenv está ativada
2. As dependências foram instaladas com `pip install -r requirements.txt`

### Erro ao ativar a virtualenv no PowerShell

Use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Alertas OpenAI não estão saindo com IA

Verifique no `.env`:

- `OPENAI_API_KEY` preenchida corretamente
- `OPENAI_ALERTS_ENABLED=True`

Se a API falhar, o sistema usa fallback local automaticamente.
