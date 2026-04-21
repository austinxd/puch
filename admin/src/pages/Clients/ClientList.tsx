import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DataTable from '../../components/DataTable'
import { listClients, type ClientListItem } from '../../api/clients'

interface Row extends ClientListItem {
  id: number
}

function formatPrice(value: string | null, moneda: string) {
  if (!value) return '-'
  const symbol = moneda === 'PEN' ? 'S/' : '$'
  return `${symbol}${Number(value).toLocaleString()}`
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' })
}

function truncate(s: string, n = 80) {
  if (!s) return ''
  return s.length > n ? `${s.slice(0, n)}…` : s
}

export default function ClientList() {
  const navigate = useNavigate()
  const [clients, setClients] = useState<ClientListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  const fetch = async (q?: string) => {
    setLoading(true)
    try {
      const data = await listClients(q)
      setClients(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch()
  }, [])

  const rows: Row[] = useMemo(
    () => clients.map((c, i) => ({ ...c, id: i + 1 })),
    [clients],
  )

  const columns = [
    {
      key: 'phone_display',
      label: 'Teléfono',
      render: (r: Row) => <span className="font-mono">{r.phone_display || r.phone}</span>,
    },
    {
      key: 'last_activity',
      label: 'Última actividad',
      render: (r: Row) => formatDate(r.last_activity),
    },
    {
      key: 'first_property',
      label: 'Primera propiedad',
      render: (r: Row) =>
        r.first_property ? (
          <span>
            <span className="font-mono text-xs text-gray-500 mr-2">{r.first_property.identificador}</span>
            {r.first_property.nombre}
          </span>
        ) : (
          <span className="text-gray-400">—</span>
        ),
    },
    {
      key: 'interested_count',
      label: 'Intereses',
      render: (r: Row) => (
        <span className="inline-flex items-center justify-center min-w-[2rem] px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
          {r.interested_count}
        </span>
      ),
    },
    {
      key: 'latest_intent',
      label: 'Última consulta',
      render: (r: Row) => {
        const i = r.latest_intent
        const parts = [i.operacion, i.tipo_propiedad, i.distritos].filter(Boolean).join(' · ')
        const price =
          i.precio_max ? `Hasta ${formatPrice(i.precio_max, 'USD')}` : ''
        return (
          <div className="max-w-md">
            <div className="text-xs text-gray-500">{[parts, price].filter(Boolean).join(' · ')}</div>
            <div className="text-sm">{truncate(i.resumen)}</div>
          </div>
        )
      },
    },
    {
      key: 'conversation_count',
      label: 'Chats',
      render: (r: Row) => r.conversation_count,
    },
  ]

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Clientes</h2>
      </div>

      <div className="flex gap-4 mb-6 flex-wrap">
        <input
          type="text"
          placeholder="Buscar por teléfono, distrito, resumen..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetch(search)}
          className="border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent w-80"
        />
        <button
          onClick={() => fetch(search)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700"
        >
          Buscar
        </button>
      </div>

      {loading ? (
        <p className="text-gray-500">Cargando...</p>
      ) : (
        <DataTable
          columns={columns}
          data={rows}
          onRowClick={(r) => navigate(`/clients/${r.phone}`)}
        />
      )}
    </div>
  )
}
