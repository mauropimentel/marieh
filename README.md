# Marieh OS

Base inicial do Marieh OS para a franquia Marieh Pilates.

## Objetivo do MVP

- Google Calendar como base da agenda operacional
- Sincronização com TotalPass e Wellhub
- Registro de check-in (SeuFisio/TotalPass) para relatórios e comissão
- Portal administrativo (Admin + Instrutor)
- Chatbot interno para operação de agenda
- Lembretes ao aluno com ação de confirmar/cancelar

## Estrutura inicial

- `docs/marieh-os-mvp.md`: arquitetura, regras de negócio e fluxos
- `apps/api/`: API FastAPI com integrações e persistência em PostgreSQL
- `apps/web/`: portal de gestão web moderno para operação diária

## Subir API (backend)

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic -c alembic.ini upgrade head
uvicorn main:app --reload --port 8080
```

Swagger: `http://localhost:8080/docs`

## Subir portal web (frontend)

```bash
cd apps/web
npm install
copy .env.example .env
npm run dev
```

Portal: `http://localhost:5173`

## Configuração de integrações (API)

Preencha `apps/api/.env` baseado em `apps/api/.env.example`:

- `DATABASE_URL`: conexão PostgreSQL do Marieh OS
- `GOOGLE_SERVICE_ACCOUNT_FILE`: caminho do JSON da service account com acesso aos calendários dos instrutores
- `TOTALPASS_*` e `WELLHUB_*`: base URL e token das APIs oficiais
- `REMINDER_WEBHOOK_URL`: endpoint do serviço que envia WhatsApp (24h e 2h)

## Persistência e migrações

- A API usa PostgreSQL via SQLAlchemy.
- Migrações são gerenciadas por Alembic em `apps/api/alembic`.
- Migração inicial: `apps/api/alembic/versions/0001_initial.py`.

Comandos úteis:

```bash
cd apps/api
alembic -c alembic.ini upgrade head
alembic -c alembic.ini downgrade -1
```

## Status da interface web

No `apps/web`, o portal já entrega:

- Cadastro de instrutores
- Criação de slots
- Criação e atualização de status de agendamentos
- Painel de alertas de reconciliação
- Métricas rápidas de operação (instrutores, slots, capacidade e agendamentos ativos)

