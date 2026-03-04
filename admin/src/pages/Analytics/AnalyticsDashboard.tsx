import { useEffect, useState } from 'react'
import api from '../../api/client'

interface TopProperty {
  identificador: string
  nombre: string
  distrito: string
  count: number
}

interface Analytics {
  total_conversations: number
  total_messages: number
  total_user_messages: number
  avg_messages_per_conversation: number
  abandonment_rate: number
  engagement_rate: number
  messages_per_day: { date: string; count: number }[]
  hour_distribution: Record<string, number>
  depth_distribution: Record<string, number>
  intents: {
    total: number
    operacion: Record<string, number>
    tipo_propiedad: Record<string, number>
    distritos: Record<string, number>
  }
  top_properties: TopProperty[]
}

interface Intent {
  id: number
  phone: string
  session_id: string
  operacion: string
  tipo_propiedad: string
  distritos: string
  precio_min: number | null
  precio_max: number | null
  habitaciones: string
  caracteristicas: string
  resumen: string
  notificado: boolean
  updated_at: string
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6 border-l-4 border-l-indigo-500">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-sm text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

function BarChart({ data, label }: { data: Record<string, number>; label: string }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1])
  const max = Math.max(...entries.map(([, v]) => v), 1)

  if (entries.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">{label}</h3>
        <p className="text-sm text-gray-400">Sin datos</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
      <h3 className="font-semibold text-gray-900 mb-4">{label}</h3>
      <div className="space-y-3">
        {entries.map(([key, value]) => (
          <div key={key}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-700">{key}</span>
              <span className="text-gray-500 font-medium">{value}</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className="bg-indigo-600 h-2 rounded-full transition-all"
                style={{ width: `${(value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function AnalyticsDashboard() {
  const [data, setData] = useState<Analytics | null>(null)
  const [intents, setIntents] = useState<Intent[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'stats' | 'intents' | 'ai'>('stats')
  const [aiAnalysis, setAiAnalysis] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiConversations, setAiConversations] = useState(0)

  useEffect(() => {
    Promise.all([
      api.get('/analytics/'),
      api.get('/intents/'),
    ]).then(([statsRes, intentsRes]) => {
      setData(statsRes.data)
      setIntents(intentsRes.data.results)
      setLoading(false)
    })
  }, [])

  const runAiAnalysis = async () => {
    setAiLoading(true)
    setAiAnalysis(null)
    try {
      const res = await api.post('/analytics/ai-analysis/')
      setAiAnalysis(res.data.analysis)
      setAiConversations(res.data.conversations_analyzed)
    } catch {
      setAiAnalysis('Error al generar el análisis. Intenta de nuevo.')
    } finally {
      setAiLoading(false)
    }
  }

  if (loading) return <p className="text-gray-500">Cargando análisis...</p>
  if (!data) return <p className="text-gray-500">Error al cargar datos</p>

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Análisis</h2>

      <div className="flex gap-2 mb-6 overflow-x-auto">
        <button
          onClick={() => setTab('stats')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'stats' ? 'bg-indigo-600 text-white shadow-sm' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Estadísticas
        </button>
        <button
          onClick={() => setTab('intents')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'intents' ? 'bg-indigo-600 text-white shadow-sm' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Intenciones ({intents.length})
        </button>
        <button
          onClick={() => setTab('ai')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'ai' ? 'bg-indigo-600 text-white shadow-sm' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Análisis IA
        </button>
      </div>

      {tab === 'stats' && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard label="Conversaciones" value={data.total_conversations} />
            <StatCard label="Mensajes totales" value={data.total_messages} />
            <StatCard
              label="Promedio msgs/conversación"
              value={data.avg_messages_per_conversation}
            />
            <StatCard
              label="Tasa de abandono"
              value={`${data.abandonment_rate}%`}
              sub="Solo 1 mensaje enviado"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard
              label="Tasa de engagement"
              value={`${data.engagement_rate}%`}
              sub="3+ mensajes enviados"
            />
            <StatCard label="Mensajes de usuarios" value={data.total_user_messages} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <BarChart data={data.depth_distribution} label="Profundidad de conversación" />
            <BarChart data={data.hour_distribution} label="Mensajes por hora" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <BarChart data={data.intents.operacion} label="Operación buscada" />
            <BarChart data={data.intents.tipo_propiedad} label="Tipo de propiedad" />
            <BarChart data={data.intents.distritos} label="Distritos de interés" />
          </div>

          {/* Top properties by first intent */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
            <h3 className="font-semibold text-gray-900 mb-4">Propiedades más buscadas (primera intención)</h3>
            {data.top_properties.length === 0 ? (
              <p className="text-sm text-gray-400">Sin datos aún</p>
            ) : (
              <div className="space-y-3">
                {data.top_properties.map((prop, i) => {
                  const max = data.top_properties[0].count
                  return (
                    <div key={prop.identificador}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-700">
                          <span className="font-mono font-medium text-indigo-600">{prop.identificador}</span>
                          {' — '}{prop.nombre}
                          {prop.distrito && <span className="text-gray-400 ml-1">({prop.distrito})</span>}
                        </span>
                        <span className="text-gray-500 font-medium">{prop.count} consulta{prop.count !== 1 ? 's' : ''}</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div
                          className="bg-indigo-600 h-2 rounded-full transition-all"
                          style={{ width: `${(prop.count / max) * 100}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </>
      )}

      {tab === 'intents' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cliente</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Operación</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Distritos</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Precio</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Resumen</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {intents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                    No hay intenciones registradas aún
                  </td>
                </tr>
              ) : (
                intents.map((intent) => (
                  <tr key={intent.id}>
                    <td className="px-4 py-3 text-sm">
                      <div>{intent.phone || intent.session_id.slice(0, 8)}</div>
                      {intent.phone && (
                        <div className="flex gap-2 mt-1">
                          <a
                            href={`https://wa.me/${intent.phone.replace(/\D/g, '')}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-green-600 hover:text-green-800 text-xs font-medium"
                          >
                            WhatsApp
                          </a>
                          <a
                            href={`tel:${intent.phone}`}
                            className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                          >
                            Llamar
                          </a>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">{intent.operacion || '-'}</td>
                    <td className="px-4 py-3 text-sm">{intent.tipo_propiedad || '-'}</td>
                    <td className="px-4 py-3 text-sm">{intent.distritos || '-'}</td>
                    <td className="px-4 py-3 text-sm">
                      {intent.precio_min || intent.precio_max
                        ? `$${intent.precio_min?.toLocaleString() || '?'} - $${intent.precio_max?.toLocaleString() || '?'}`
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm max-w-xs truncate">{intent.resumen || '-'}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        intent.notificado
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {intent.notificado ? 'Notificado' : 'Pendiente'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'ai' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-gray-900">Análisis de estrategias de cierre</h3>
              <p className="text-sm text-gray-500">Analiza conversaciones recientes con IA para identificar oportunidades de venta</p>
            </div>
            <button
              onClick={runAiAnalysis}
              disabled={aiLoading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-xl shadow-sm text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {aiLoading ? 'Analizando...' : 'Iniciar análisis'}
            </button>
          </div>

          {aiLoading && (
            <div className="flex items-center gap-3 py-8 justify-center">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600" />
              <span className="text-gray-500">Analizando conversaciones con IA...</span>
            </div>
          )}

          {aiAnalysis && !aiLoading && (
            <div>
              <p className="text-xs text-gray-400 mb-3">{aiConversations} conversaciones analizadas</p>
              <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                {aiAnalysis}
              </div>
            </div>
          )}

          {!aiAnalysis && !aiLoading && (
            <p className="text-gray-400 text-sm py-8 text-center">
              Haz clic en "Iniciar análisis" para generar recomendaciones basadas en las conversaciones recientes.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
