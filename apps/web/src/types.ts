export type BookingStatus = 'created' | 'confirmed' | 'cancelled' | 'attended'
export type BookingSource = 'totalpass' | 'wellhub' | 'manual' | 'portal'

export interface Instructor {
  id: string
  name: string
  max_students_per_slot: number
  google_calendar_id: string
}

export interface ClassSlot {
  id: string
  instructor_id: string
  start_at: string
  end_at: string
  capacity: number
}

export interface Booking {
  id: string
  slot_id: string
  student_cpf: string
  student_name: string
  source: BookingSource
  status: BookingStatus
  external_id?: string | null
  google_event_id?: string | null
  created_at: string
  updated_at: string
}

export interface Alert {
  id: string
  booking_id?: string | null
  kind: string
  message: string
  created_at: string
}

