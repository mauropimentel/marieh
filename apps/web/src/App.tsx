import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'

import { api } from './api'
import './App.css'
import type { Alert, Booking, BookingStatus, ClassSlot, Instructor } from './types'

const surfaceMotion = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.35 },
}

function App() {
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')

  const [instructors, setInstructors] = useState<Instructor[]>([])
  const [slots, setSlots] = useState<ClassSlot[]>([])
  const [bookings, setBookings] = useState<Booking[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])

  const [instructorForm, setInstructorForm] = useState({
    name: '',
    max_students_per_slot: 5,
    google_calendar_id: '',
  })

  const [slotForm, setSlotForm] = useState({
    instructor_id: '',
    start_at: '',
    end_at: '',
    capacity: 8,
  })

  const [bookingForm, setBookingForm] = useState({
    slot_id: '',
    cpf: '',
    full_name: '',
    source: 'totalpass' as Booking['source'],
    external_id: '',
  })

  const slotLabelById = useMemo(() => {
    const byInstructor = new Map(instructors.map((item) => [item.id, item.name]))
    return new Map(
      slots.map((slot) => [
        slot.id,
        `${new Date(slot.start_at).toLocaleString('pt-BR', {
          dateStyle: 'short',
          timeStyle: 'short',
        })} · ${byInstructor.get(slot.instructor_id) ?? 'Instrutor não encontrado'}`,
      ]),
    )
  }, [instructors, slots])

  const totalCapacity = slots.reduce((acc, slot) => acc + slot.capacity, 0)
  const activeBookings = bookings.filter((item) => item.status !== 'cancelled').length

  async function loadDashboard() {
    setErrorMessage('')
    try {
      const [instructorData, slotData, bookingData, alertData] = await Promise.all([
        api.listInstructors(),
        api.listSlots(),
        api.listBookings(),
        api.listAlerts(),
      ])

      setInstructors(instructorData)
      setSlots(slotData)
      setBookings(bookingData)
      setAlerts(alertData)

      if (!slotForm.instructor_id && instructorData.length > 0) {
        setSlotForm((current) => ({ ...current, instructor_id: instructorData[0].id }))
      }
      if (!bookingForm.slot_id && slotData.length > 0) {
        setBookingForm((current) => ({ ...current, slot_id: slotData[0].id }))
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Falha ao carregar dados')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  async function handleCreateInstructor(event: FormEvent) {
    event.preventDefault()
    try {
      await api.createInstructor(instructorForm)
      setInstructorForm({ name: '', max_students_per_slot: 5, google_calendar_id: '' })
      await loadDashboard()
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Erro ao criar instrutor')
    }
  }

  async function handleCreateSlot(event: FormEvent) {
    event.preventDefault()
    try {
      await api.createSlot(slotForm)
      setSlotForm((current) => ({ ...current, start_at: '', end_at: '', capacity: 8 }))
      await loadDashboard()
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Erro ao criar slot')
    }
  }

  async function handleCreateBooking(event: FormEvent) {
    event.preventDefault()
    try {
      await api.createBooking({
        ...bookingForm,
        external_id: bookingForm.external_id || undefined,
      })
      setBookingForm((current) => ({ ...current, cpf: '', full_name: '', external_id: '' }))
      await loadDashboard()
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Erro ao criar agendamento')
    }
  }

  async function handleStatusChange(bookingId: string, status: BookingStatus) {
    try {
      await api.updateBookingStatus(bookingId, status)
      await loadDashboard()
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Erro ao atualizar status')
    }
  }

  return (
    <div className="app-shell">
      <aside className="left-rail">
        <motion.div {...surfaceMotion} className="brand-block">
          <p className="eyebrow">Marieh OS</p>
          <h1>Gestão da operação Marieh Pilates</h1>
          <p className="support-copy">
            Agenda centralizada, sincronização com parceiros e visão de ocupação em um único ambiente.
          </p>
        </motion.div>

        <motion.div {...surfaceMotion} transition={{ ...surfaceMotion.transition, delay: 0.06 }}>
          <dl className="stats-list">
            <div>
              <dt>Instrutores</dt>
              <dd>{instructors.length}</dd>
            </div>
            <div>
              <dt>Slots ativos</dt>
              <dd>{slots.length}</dd>
            </div>
            <div>
              <dt>Capacidade total</dt>
              <dd>{totalCapacity}</dd>
            </div>
            <div>
              <dt>Agendamentos ativos</dt>
              <dd>{activeBookings}</dd>
            </div>
          </dl>
        </motion.div>

        <motion.button
          {...surfaceMotion}
          transition={{ ...surfaceMotion.transition, delay: 0.12 }}
          className="refresh-action"
          onClick={loadDashboard}
        >
          Atualizar dados
        </motion.button>
      </aside>

      <main className="workspace">
        <AnimatePresence>
          {errorMessage && (
            <motion.p
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="error-banner"
            >
              {errorMessage}
            </motion.p>
          )}
        </AnimatePresence>

        <section className="panel-grid">
          <motion.section {...surfaceMotion} className="panel">
            <header className="panel-header">
              <h2>Instrutores</h2>
              <p>Cadastre profissional e capacidade por aula.</p>
            </header>
            <form className="inline-form" onSubmit={handleCreateInstructor}>
              <input
                placeholder="Nome"
                value={instructorForm.name}
                onChange={(event) => setInstructorForm((current) => ({ ...current, name: event.target.value }))}
                required
              />
              <input
                placeholder="Capacidade"
                type="number"
                min={1}
                max={20}
                value={instructorForm.max_students_per_slot}
                onChange={(event) =>
                  setInstructorForm((current) => ({ ...current, max_students_per_slot: Number(event.target.value) }))
                }
                required
              />
              <input
                placeholder="Google Calendar ID"
                value={instructorForm.google_calendar_id}
                onChange={(event) =>
                  setInstructorForm((current) => ({ ...current, google_calendar_id: event.target.value }))
                }
                required
              />
              <button type="submit">Salvar instrutor</button>
            </form>
            <ul className="data-list">
              {instructors.map((item) => (
                <li key={item.id}>
                  <strong>{item.name}</strong>
                  <span>{item.max_students_per_slot} alunos por slot</span>
                </li>
              ))}
            </ul>
          </motion.section>

          <motion.section {...surfaceMotion} transition={{ ...surfaceMotion.transition, delay: 0.06 }} className="panel">
            <header className="panel-header">
              <h2>Slots de aula</h2>
              <p>Abra disponibilidade com horário e capacidade.</p>
            </header>
            <form className="inline-form" onSubmit={handleCreateSlot}>
              <select
                value={slotForm.instructor_id}
                onChange={(event) => setSlotForm((current) => ({ ...current, instructor_id: event.target.value }))}
                required
              >
                <option value="">Selecione instrutor</option>
                {instructors.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
              <input
                type="datetime-local"
                value={slotForm.start_at}
                onChange={(event) => setSlotForm((current) => ({ ...current, start_at: event.target.value }))}
                required
              />
              <input
                type="datetime-local"
                value={slotForm.end_at}
                onChange={(event) => setSlotForm((current) => ({ ...current, end_at: event.target.value }))}
                required
              />
              <input
                type="number"
                min={1}
                max={30}
                value={slotForm.capacity}
                onChange={(event) => setSlotForm((current) => ({ ...current, capacity: Number(event.target.value) }))}
                required
              />
              <button type="submit">Criar slot</button>
            </form>
            <ul className="data-list compact">
              {slots.map((item) => (
                <li key={item.id}>
                  <strong>
                    {new Date(item.start_at).toLocaleString('pt-BR', {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    })}
                  </strong>
                  <span>Capacidade {item.capacity}</span>
                </li>
              ))}
            </ul>
          </motion.section>
        </section>

        <section className="panel-grid stacked">
          <motion.section {...surfaceMotion} transition={{ ...surfaceMotion.transition, delay: 0.1 }} className="panel">
            <header className="panel-header">
              <h2>Agendamentos</h2>
              <p>Crie, confirme e cancele reservas sem sair da operação.</p>
            </header>
            <form className="inline-form booking-form" onSubmit={handleCreateBooking}>
              <select
                value={bookingForm.slot_id}
                onChange={(event) => setBookingForm((current) => ({ ...current, slot_id: event.target.value }))}
                required
              >
                <option value="">Selecione slot</option>
                {slots.map((item) => (
                  <option key={item.id} value={item.id}>
                    {slotLabelById.get(item.id)}
                  </option>
                ))}
              </select>
              <input
                placeholder="CPF"
                value={bookingForm.cpf}
                onChange={(event) => setBookingForm((current) => ({ ...current, cpf: event.target.value }))}
                required
              />
              <input
                placeholder="Nome completo"
                value={bookingForm.full_name}
                onChange={(event) => setBookingForm((current) => ({ ...current, full_name: event.target.value }))}
                required
              />
              <select
                value={bookingForm.source}
                onChange={(event) => setBookingForm((current) => ({ ...current, source: event.target.value as Booking['source'] }))}
              >
                <option value="totalpass">TotalPass</option>
                <option value="wellhub">Wellhub</option>
                <option value="manual">Manual</option>
                <option value="portal">Portal</option>
              </select>
              <input
                placeholder="ID externo (opcional)"
                value={bookingForm.external_id}
                onChange={(event) => setBookingForm((current) => ({ ...current, external_id: event.target.value }))}
              />
              <button type="submit">Criar agendamento</button>
            </form>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Aluno</th>
                    <th>Slot</th>
                    <th>Status</th>
                    <th>Origem</th>
                    <th>Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {bookings.map((item) => (
                    <motion.tr
                      key={item.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.2 }}
                    >
                      <td>{item.student_name}</td>
                      <td>{slotLabelById.get(item.slot_id) ?? item.slot_id}</td>
                      <td>
                        <span className={`status status-${item.status}`}>{item.status}</span>
                      </td>
                      <td>{item.source}</td>
                      <td>
                        <select
                          value={item.status}
                          onChange={(event) => handleStatusChange(item.id, event.target.value as BookingStatus)}
                        >
                          <option value="created">created</option>
                          <option value="confirmed">confirmed</option>
                          <option value="cancelled">cancelled</option>
                          <option value="attended">attended</option>
                        </select>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.section>

          <motion.section {...surfaceMotion} transition={{ ...surfaceMotion.transition, delay: 0.14 }} className="panel">
            <header className="panel-header">
              <h2>Alertas de reconciliação</h2>
              <p>Eventos que exigem revisão entre parceiros e Google Calendar.</p>
            </header>
            <ul className="data-list alerts">
              {alerts.map((item) => (
                <li key={item.id}>
                  <strong>{item.kind}</strong>
                  <span>{item.message}</span>
                  <small>
                    {new Date(item.created_at).toLocaleString('pt-BR', {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    })}
                  </small>
                </li>
              ))}
            </ul>
          </motion.section>
        </section>
      </main>

      {isLoading && <div className="loading-overlay">Carregando Marieh OS…</div>}
    </div>
  )
}

export default App



