import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api/client'
import DataTable from '../../components/DataTable'

interface Property {
  id: number
  identificador: string
  nombre: string
  clase: string
  operacion: string
  distrito: string
  precio: string | null
  moneda: string
  agent_name: string
  activo: boolean
  first_image: string | null
}

export default function PropertyList() {
  const navigate = useNavigate()
  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ clase: '', operacion: '', distrito: '', search: '' })

  const fetchProperties = async () => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (filters.clase) params.clase = filters.clase
    if (filters.operacion) params.operacion = filters.operacion
    if (filters.distrito) params.distrito = filters.distrito
    if (filters.search) params.search = filters.search
    const res = await api.get('/properties/', { params })
    setProperties(res.data.results)
    setLoading(false)
  }

  useEffect(() => {
    fetchProperties()
  }, [filters.clase, filters.operacion, filters.distrito])

  const handleDelete = async (id: number) => {
    if (!confirm('¿Eliminar esta propiedad?')) return
    await api.delete(`/properties/${id}/`)
    fetchProperties()
  }

  const columns = [
    { key: 'identificador', label: 'ID' },
    { key: 'nombre', label: 'Nombre' },
    { key: 'clase', label: 'Clase' },
    { key: 'operacion', label: 'Operación' },
    { key: 'distrito', label: 'Distrito' },
    {
      key: 'precio',
      label: 'Precio',
      render: (p: Property) => p.precio ? `${p.moneda === 'PEN' ? 'S/' : '$'}${Number(p.precio).toLocaleString()}` : '-',
    },
    { key: 'agent_name', label: 'Agente' },
    {
      key: 'activo',
      label: 'Estado',
      render: (p: Property) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${p.activo ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {p.activo ? 'Activo' : 'Inactivo'}
        </span>
      ),
    },
    {
      key: 'actions',
      label: '',
      render: (p: Property) => (
        <div className="flex gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); navigate(`/properties/${p.id}/edit`) }}
            className="text-indigo-600 hover:text-indigo-800 text-sm"
          >
            Editar
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleDelete(p.id) }}
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
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Propiedades</h2>
        <button
          onClick={() => navigate('/properties/new')}
          className="w-full sm:w-auto bg-indigo-600 text-white px-4 py-2 rounded-xl shadow-sm hover:bg-indigo-700 transition-colors"
        >
          + Nueva Propiedad
        </button>
      </div>

      <div className="flex gap-4 mb-6 flex-wrap">
        <input
          type="text"
          placeholder="Buscar..."
          value={filters.search}
          onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          onKeyDown={(e) => e.key === 'Enter' && fetchProperties()}
          className="border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
        <select
          value={filters.clase}
          onChange={(e) => setFilters({ ...filters, clase: e.target.value })}
          className="border border-gray-300 rounded-lg px-4 py-2 text-sm"
        >
          <option value="">Todas las clases</option>
          <option value="Residencial">Residencial</option>
          <option value="Comercial">Comercial</option>
          <option value="Industrial">Industrial</option>
        </select>
        <select
          value={filters.operacion}
          onChange={(e) => setFilters({ ...filters, operacion: e.target.value })}
          className="border border-gray-300 rounded-lg px-4 py-2 text-sm"
        >
          <option value="">Todas las operaciones</option>
          <option value="Venta">Venta</option>
          <option value="Alquiler">Alquiler</option>
        </select>
      </div>

      {loading ? (
        <p className="text-gray-500">Cargando...</p>
      ) : (
        <DataTable
          columns={columns}
          data={properties}
          onRowClick={(p) => navigate(`/properties/${p.id}`)}
        />
      )}
    </div>
  )
}
