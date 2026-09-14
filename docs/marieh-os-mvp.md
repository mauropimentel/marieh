# Marieh OS — Arquitetura MVP

## 1) Decisões fechadas para o MVP

- Fonte de verdade de agenda: Google Calendar (calendários por instrutor)
- Canais:
  - Equipe: chatbot no portal
  - Aluno: WhatsApp para lembrete + confirmar/cancelar
- Integrações: API oficial + webhooks (TotalPass e Wellhub)
- Identidade única do aluno: CPF (obrigatório para vínculo automático)
- Comissão: baseada em check-in confirmado
- Limite de janela de agendamento no parceiro: 15 dias
- Política de conflito: mudança em app parceiro prevalece e gera alerta para ajuste no Google Calendar
- Cancelamento: sem trava automática no v1 (somente registro)

## 2) Modelo operacional

### Calendário

- Cada instrutor possui um calendário próprio
- Cada aula tem duração de 50 min + 10 min de intervalo (slot de 1h)
- Capacidade por instrutor é configurável (ex: 4 ou 5)
- Capacidade total publicada no TotalPass/Wellhub deve refletir disponibilidade real somada dos instrutores no slot
- Qualquer alteração de agenda deve disparar sincronização imediata para evitar overbooking

### Agendamentos

- Origem principal: TotalPass e Wellhub
- Origem secundária: manual (Instagram/recepção)
- Mudanças possíveis: criar, remarcar, cancelar, confirmar presença
- Chave de reconciliação entre plataformas: CPF
- Sem CPF: registro pendente para análise manual no portal

### Check-in e comissão

- Check-in recebido (TotalPass/SeuFisio) alimenta relatório de presença
- Comissão por instrutor é calculada com base em check-ins confirmados
- Deve guardar vínculo: aluno + instrutor + horário + origem do check-in

## 3) Arquitetura sugerida

### Componentes

1. **API Core (Marieh OS)**
   - Regras de agendamento
   - Reconciliação de conflitos
   - Logs de auditoria
   - Gestão de instrutores/capacidade

2. **Sync Engine**
   - Consumidor de webhooks TotalPass/Wellhub
   - Publicação de disponibilidade para parceiros
   - Sincronização bidirecional com Google Calendar

3. **Notification Engine**
   - Disparo de lembretes (24h e 2h)
   - Captura de respostas confirmar/cancelar via WhatsApp

4. **Portal Web**
   - Perfil Admin e Instrutor
   - Painel de agenda
   - Conciliação pendente
   - Relatórios de presença, ocupação e comissão

### Persistência (MVP)

- `students`: CPF, nome, telefone, origem
- `instructors`: capacidade por slot, calendário Google
- `class_slots`: início/fim, capacidade total, instrutores alocados
- `bookings`: status, origem, ids externos, timestamps
- `attendance_checkins`: fonte, status, referência externa
- `sync_events`: payload bruto, status processamento, erros
- `alerts`: conflitos e ações pendentes de reconciliação

## 4) Fluxos críticos

### Fluxo A — Agendamento vindo do parceiro

1. Webhook recebe agendamento TotalPass/Wellhub
2. Valida identidade (CPF)
3. Reserva no Marieh OS
4. Atualiza evento no Google Calendar do instrutor
5. Recalcula disponibilidade e republica nos parceiros

### Fluxo B — Mudança no Google Calendar

1. Mudança capturada por watcher/polling
2. Atualiza estado interno do slot
3. Publica nova disponibilidade no TotalPass/Wellhub
4. Gera auditoria de sincronização

### Fluxo C — Conflito simultâneo

1. Mudança chega do parceiro enquanto agenda divergiu
2. Parceiro prevalece no estado de reserva
3. Marieh OS abre alerta de ajuste no Google Calendar
4. Operação resolve no portal/chatbot

### Fluxo D — Lembrete e resposta

1. T-24h e T-2h dispara WhatsApp
2. Aluno confirma/cancela
3. Marieh OS atualiza booking
4. Sincroniza alteração com Google Calendar e parceiros

## 5) Integrações externas

- **Google Calendar (base)**
  - Criação/edição/cancelamento de eventos
  - Leitura de disponibilidade por instrutor
  - Notificação de alterações

- **TotalPass / Wellhub**
  - Publicação de disponibilidade
  - Recepção de agendamentos/cancelamentos
  - Confirmação de estado final

- **SeuFisio**
  - Entrada de check-in
  - Enriquecimento de dados para comissão

## 6) Métricas mínimas do portal

- Taxa de ocupação por horário/instrutor
- Taxa de cancelamento e no-show
- Check-ins confirmados por período
- Comissão por instrutor
- Conflitos de sincronização abertos/fechados

