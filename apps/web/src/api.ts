import type { Alert, Booking, BookingStatus, ClassSlot, Instructor } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    let detail = 'Erro inesperado ao chamar API'
    try {
      const body = await response.json()
      detail = body.detail ?? detail
    } catch {
      detail = response.statusText || detail
    }
    throw new Error(detail)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string; service: string }>('/health'),

  listInstructors: () => request<Instructor[]>('/instructors'),
  createInstructor: (payload: {
    name: string
    max_students_per_slot: number
    google_calendar_id: string
  }) => request<Instructor>('/instructors', { method: 'POST', body: JSON.stringify(payload) }),

  listSlots: () => request<ClassSlot[]>('/slots'),
  createSlot: (payload: {
    instructor_id: string
    start_at: string
    end_at: string
    capacity: number
  }) => request<ClassSlot>('/slots', { method: 'POST', body: JSON.stringify(payload) }),

  listBookings: () => request<Booking[]>('/bookings'),
  createBooking: (payload: {
    slot_id: string
    cpf: string
    full_name: string
    source: 'totalpass' | 'wellhub' | 'manual' | 'portal'
    external_id?: string
  }) => request<Booking>('/bookings', { method: 'POST', body: JSON.stringify(payload) }),
  updateBookingStatus: (bookingId: string, status: BookingStatus) =>
    request<Booking>(`/bookings/${bookingId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),

  listAlerts: () => request<Alert[]>('/alerts'),
}

