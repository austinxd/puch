import { useEffect, useState } from 'react'
import api from '../../api/client'
import DataTable from '../../components/DataTable'

interface Appointment {
  id: number
  property_identifier: string
  property_name: string
  agent_name: string
  client_name: string
  client_phone: string
  datetime_start: string
  status: string
}

const statusLabels: Record<string, { label: string; className: string }> = {
  scheduled: { label: 'Programada', className: 'bg-blue-50 text-blue-700' },
  cancelled: { label: 'Cancelada', className: 'bg-red-50 text-red-700' },
  completed: { label: 'Completada', className: 'bg-green-50 text-green-700' },
}

export default function AppointmentList() {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/appointments/').then((res) => {
      setAppointments(res.data.results)
      setLoading(false)
    })
  }, [])

  const columns = [
    { key: 'client_name', label: 'Cliente' },
    { key: 'client_phone', label: 'Teléfono' },
    {
      key: 'property_identifier',
      label: 'Propiedad',
      render: (a: Appointment) => (
        <span title={a.property_name}>{a.property_identifier}</span>
      ),
    },
    { key: 'agent_name', label: 'Agente' },
    {
      key: 'datetime_start',
      label: 'Fecha y Hora',
      render: (a: Appointment) => {
        const d = new Date(a.datetime_start)
        return d.toLocaleString('es-PE', {
          dateStyle: 'medium',
          timeStyle: 'short',
        })
      },
    },
    {
      key: 'status',
      label: 'Estado',
      render: (a: Appointment) => {
        const s = statusLabels[a.status] || { label: a.status, className: 'bg-gray-50 text-gray-700' }
        return (
          <span className={`text-xs px-2 py-0.5 rounded-full ${s.className}`}>
            {s.label}
          </span>
        )
      },
    },
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Citas</h2>
      </div>

      {loading ? (
        <p className="text-gray-500">Cargando...</p>
      ) : (
        <DataTable columns={columns} data={appointments} />
      )}
    </div>
  )
}
