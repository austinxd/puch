import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api/client'
import DataTable from '../../components/DataTable'

interface Agent {
  id: number
  name: string
  phone: string
  email: string
}

export default function AgentList() {
  const navigate = useNavigate()
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  const fetchAgents = async () => {
    setLoading(true)
    const res = await api.get('/agents/')
    setAgents(res.data.results)
    setLoading(false)
  }

  useEffect(() => {
    fetchAgents()
  }, [])

  const handleDelete = async (id: number) => {
    if (!confirm('¿Eliminar este agente?')) return
    await api.delete(`/agents/${id}/`)
    fetchAgents()
  }

  const columns = [
    { key: 'name', label: 'Nombre' },
    { key: 'phone', label: 'Teléfono' },
    { key: 'email', label: 'Email' },
    {
      key: 'actions',
      label: '',
      render: (a: Agent) => (
        <div className="flex gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); navigate(`/agents/${a.id}/edit`) }}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            Editar
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleDelete(a.id) }}
            className="text-red-600 hover:text-red-800 text-sm"
          >
            Eliminar
          </button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Agentes</h2>
        <button
          onClick={() => navigate('/agents/new')}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Nuevo Agente
        </button>
      </div>

      {loading ? (
        <p className="text-gray-500">Cargando...</p>
      ) : (
        <DataTable columns={columns} data={agents} />
      )}
    </div>
  )
}
