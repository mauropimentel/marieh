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

## API local (esqueleto)

```bash
cd apps/api
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

Swagger: `http://localhost:8080/docs`

## Próximos passos sugeridos

1. Conectar Google Calendar (MCP/Google API) no `GoogleCalendarAdapter`
2. Conectar TotalPass/Wellhub em `PartnerSyncAdapter`
3. Persistência real (PostgreSQL)
4. Portal web (Next.js) consumindo esta API
5. Automação de lembretes (WhatsApp)

