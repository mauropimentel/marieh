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
- `apps/api/`: API inicial com regras centrais de agenda e sincronização

## API local

```bash
cd apps/api
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8080
```

Swagger: `http://localhost:8080/docs`

## Configuração de integrações

Preencha `apps/api/.env` baseado em `apps/api/.env.example`:

- `DATABASE_URL`: conexão PostgreSQL do Marieh OS
- `GOOGLE_SERVICE_ACCOUNT_FILE`: caminho do JSON da service account com acesso aos calendários dos instrutores
- `TOTALPASS_*` e `WELLHUB_*`: base URL e token das APIs oficiais
- `REMINDER_WEBHOOK_URL`: endpoint do serviço que envia WhatsApp (24h e 2h)

## Persistência

- A API usa PostgreSQL via SQLAlchemy.
- As tabelas são criadas automaticamente no startup (`Base.metadata.create_all`).
- Próximo passo recomendado: adicionar migrações com Alembic.

## Próximos passos sugeridos

1. Ajustar payload/rotas finais de disponibilidade TotalPass/Wellhub
2. Ligar webhook oficial dos parceiros em `POST /webhooks/partners`
3. Implementar relatórios de ocupação/comissão em SQL
4. Portal web (Next.js) consumindo esta API
