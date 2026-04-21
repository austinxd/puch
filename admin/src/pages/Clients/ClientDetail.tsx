import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getClient, type ClientDetail, type PropertySummary } from '../../api/clients'

function formatPrice(value: string | null, moneda: string) {
  if (!value) return '-'
  const symbol = moneda === 'PEN' ? 'S/' : '$'
  return `${symbol}${Number(value).toLocaleString()}`
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' })
}

function PropertyCard({
  prop,
  meta,
}: {
  prop: PropertySummary
  meta?: React.ReactNode
}) {
  return (
    <Link
      to={`/properties/${prop.id}`}
      className="flex gap-4 p-4 bg-white border border-gray-200 rounded-xl hover:shadow-md transition-shadow"
    >
      <div className="w-24 h-24 flex-shrink-0 rounded-lg overflow-hidden bg-gray-100">
        {prop.image_url ? (
          <img src={prop.image_url} alt={prop.nombre} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">
            sin foto
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs font-mono text-gray-500">{prop.identificador}</div>
        <div className="font-medium text-gray-900 truncate">{prop.nombre}</div>
        <div className="text-sm text-gray-600">
          {[prop.tipologia, prop.distrito].filter(Boolean).join(' · ')}
        </div>
        <div className="text-sm font-semibold text-indigo-700 mt-1">
          {formatPrice(prop.precio, prop.moneda)}
        </div>
        {meta}
      </div>
    </Link>
  )
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
      {children}
    </span>
  )
}

export default function ClientDetailPage() {
  const { phone } = useParams<{ phone: string }>()
  const navigate = useNavigate()
  const [client, setClient] = useState<ClientDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!phone) return
    setLoading(true)
    getClient(phone)
      .then(setClient)
      .catch((e) => setError(e?.response?.data?.error || 'Error cargando cliente'))
      .finally(() => setLoading(false))
  }, [phone])

  if (loading) return <p className="text-gray-500">Cargando...</p>
  if (error) return <p className="text-red-600">{error}</p>
  if (!client) return null

  const intent = client.latest_intent

  return (
    <div className="space-y-8">
      <div>
        <button
          onClick={() => navigate('/clients')}
          className="text-sm text-indigo-600 hover:text-indigo-800 mb-3"
        >
          ← Volver a Clientes
        </button>
        <h2 className="text-2xl font-bold text-gray-900 font-mono">
          {client.phone_display || client.phone}
        </h2>
        {intent && (
          <div className="mt-3 flex flex-wrap gap-2">
            {intent.operacion && <Chip>{intent.operacion}</Chip>}
            {intent.tipo_propiedad && <Chip>{intent.tipo_propiedad}</Chip>}
            {intent.distritos && <Chip>{intent.distritos}</Chip>}
            {intent.precio_max && <Chip>Hasta {formatPrice(intent.precio_max, 'USD')}</Chip>}
            {intent.habitaciones && <Chip>{intent.habitaciones} hab</Chip>}
          </div>
        )}
        {intent?.resumen && (
          <p className="mt-4 text-gray-700 bg-amber-50 border border-amber-100 rounded-lg p-3 text-sm">
            {intent.resumen}
          </p>
        )}
      </div>

      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          Primera propiedad consultada
        </h3>
        {client.conversations.length > 0 && client.conversations[client.conversations.length - 1].first_property ? (
          <PropertyCard prop={client.conversations[client.conversations.length - 1].first_property!} />
        ) : (
          <p className="text-gray-500 text-sm">Sin propiedad de entrada registrada.</p>
        )}
      </section>

      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          Propiedades de interés ({client.interested_properties.length})
        </h3>
        {client.interested_properties.length === 0 ? (
          <p className="text-gray-500 text-sm">
            Aún no se registraron propiedades mostradas a este cliente.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {client.interested_properties.map((ip) => (
              <PropertyCard
                key={ip.property.id}
                prop={ip.property}
                meta={
                  <div className="text-xs text-gray-500 mt-1">
                    Mostrada {ip.shown_count}× · última {formatDate(ip.last_shown_at)}
                  </div>
                }
              />
            ))}
          </div>
        )}
      </section>

      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          Conversaciones ({client.conversations.length})
        </h3>
        <div className="space-y-2">
          {client.conversations.map((conv) => (
            <Link
              key={conv.session_id}
              to={`/assistant?session=${conv.session_id}`}
              className="block p-4 bg-white border border-gray-200 rounded-xl hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start gap-3">
                <div className="min-w-0">
                  <div className="text-xs font-mono text-gray-500 truncate">
                    {conv.session_id}
                  </div>
                  <div className="text-sm text-gray-700 mt-1">
                    {conv.message_count} mensajes · agente{' '}
                    {conv.agent_name || <span className="text-gray-400">sin asignar</span>}
                  </div>
                </div>
                <div className="text-xs text-gray-500 text-right flex-shrink-0">
                  <div>creado {formatDate(conv.created_at)}</div>
                  <div>último {formatDate(conv.last_message_at)}</div>
                </div>
              </div>
              {conv.first_property && (
                <div className="mt-2 text-xs text-gray-600">
                  Entró por <span className="font-mono">{conv.first_property.identificador}</span>{' '}
                  — {conv.first_property.nombre}
                </div>
              )}
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
