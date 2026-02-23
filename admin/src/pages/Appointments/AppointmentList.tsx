import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api/client'

interface CalendarEvent {
  id: string
  title: string
  start: string
  end: string
  location: string
  description: string
  agent_id: number
  agent_name: string
}

interface Appointment {
  id: number
  property_identifier: string
  property_name: string
  agent_name: string
  client_name: string
  client_phone: string
  datetime_start: string
  datetime_end: string
  status: string
  conversation_session_id: string | null
}

const statusLabels: Record<string, { label: string; className: string }> = {
  scheduled: { label: 'Programada', className: 'bg-blue-50 text-blue-700 border-blue-200' },
  cancelled: { label: 'Cancelada', className: 'bg-red-50 text-red-700 border-red-200' },
  completed: { label: 'Completada', className: 'bg-green-50 text-green-700 border-green-200' },
}

function formatTime(dateStr: string) {
  const d = new Date(dateStr)
  return d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('es-PE', { weekday: 'long', day: 'numeric', month: 'long' })
}

function groupByDate(events: CalendarEvent[]): Record<string, CalendarEvent[]> {
  const groups: Record<string, CalendarEvent[]> = {}
  for (const event of events) {
    const dateKey = event.start.split('T')[0]
    if (!groups[dateKey]) groups[dateKey] = []
    groups[dateKey].push(event)
  }
  return groups
}

export default function AppointmentList() {
  const navigate = useNavigate()
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState<'calendar' | 'appointments'>('calendar')

  useEffect(() => {
    const today = new Date()
    const from = today.toISOString().split('T')[0]
    const to = new Date(today.getTime() + 30 * 86400000).toISOString().split('T')[0]

    Promise.all([
      api.get('/calendar/events/', { params: { from, to } }),
      api.get('/appointments/'),
    ]).then(([eventsRes, apptRes]) => {
      setEvents(eventsRes.data)
      setAppointments(apptRes.data.results)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const grouped = groupByDate(events)
  const sortedDates = Object.keys(grouped).sort()

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Citas y Agenda</h2>
        <div className="flex bg-gray-100 rounded-lg p-1 self-center sm:self-auto">
          <button
            onClick={() => setView('calendar')}
            className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
              view === 'calendar' ? 'bg-white shadow text-gray-900' : 'text-gray-500'
            }`}
          >
            Agenda Google
          </button>
          <button
            onClick={() => setView('appointments')}
            className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
              view === 'appointments' ? 'bg-white shadow text-gray-900' : 'text-gray-500'
            }`}
          >
            Citas Chatbot
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-gray-500">Cargando...</p>
      ) : view === 'calendar' ? (
        <div className="space-y-6">
          {sortedDates.length === 0 ? (
            <p className="text-gray-500 text-center py-12">No hay eventos en los próximos 30 días</p>
          ) : (
            sortedDates.map((dateKey) => (
              <div key={dateKey}>
                <h3 className="text-sm font-semibold text-gray-500 uppercase mb-3">
                  {formatDate(grouped[dateKey][0].start)}
                </h3>
                <div className="space-y-2">
                  {grouped[dateKey].map((event) => (
                    <div
                      key={event.id}
                      className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4 flex gap-4"
                    >
                      <div className="text-right shrink-0 w-20">
                        <p className="text-sm font-semibold text-gray-900">{formatTime(event.start)}</p>
                        <p className="text-xs text-gray-400">{formatTime(event.end)}</p>
                      </div>
                      <div className="border-l-4 border-blue-500 pl-4 flex-1">
                        <p className="font-medium text-gray-900">{event.title}</p>
                        {event.location && (
                          <p className="text-sm text-gray-500 mt-1">{event.location}</p>
                        )}
                        {event.description && (
                          <p className="text-xs text-gray-400 mt-1 whitespace-pre-wrap line-clamp-2">{event.description}</p>
                        )}
                        <p className="text-xs text-gray-400 mt-2">Agente: {event.agent_name}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {appointments.length === 0 ? (
            <p className="text-gray-500 text-center py-12">No hay citas del chatbot</p>
          ) : (
            appointments.map((a) => {
              const s = statusLabels[a.status] || { label: a.status, className: 'bg-gray-50 text-gray-700 border-gray-200' }
              return (
                <div key={a.id} className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4 flex gap-4">
                  <div className="text-right shrink-0 w-20">
                    <p className="text-sm font-semibold text-gray-900">{formatTime(a.datetime_start)}</p>
                    <p className="text-xs text-gray-400">{formatTime(a.datetime_end)}</p>
                  </div>
                  <div className="border-l-4 border-green-500 pl-4 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-gray-900">{a.client_name}</p>
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${s.className}`}>{s.label}</span>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">{a.property_identifier} - {a.property_name}</p>
                    {a.client_phone && (
                      <p className="text-xs text-gray-400 mt-1">Tel: {a.client_phone}</p>
                    )}
                    <p className="text-xs text-gray-400 mt-1">
                      {formatDate(a.datetime_start)} | Agente: {a.agent_name}
                    </p>
                    {a.conversation_session_id && (
                      <button
                        onClick={() => navigate(`/assistant?chat=${a.conversation_session_id}`)}
                        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        Ver conversación
                      </button>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
