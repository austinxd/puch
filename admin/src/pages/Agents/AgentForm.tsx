import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import api from '../../api/client'

interface AgentFormData {
  name: string
  phone: string
  email: string
  username: string
  password: string
  google_calendar_connected?: boolean
}

export default function AgentForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<AgentFormData>({ name: '', phone: '', email: '', username: '', password: '' })
  const [saving, setSaving] = useState(false)
  const [googleStatus, setGoogleStatus] = useState<string | null>(null)

  useEffect(() => {
    if (isEdit) {
      api.get(`/agents/${id}/`).then((res) => setForm({ ...res.data, password: '' }))
    }
  }, [id])

  useEffect(() => {
    const googleParam = searchParams.get('google')
    if (googleParam === 'connected') {
      setGoogleStatus('connected')
      if (id) api.get(`/agents/${id}/`).then((res) => setForm({ ...res.data, password: '' }))
    } else if (googleParam === 'error') {
      setGoogleStatus('error')
    }
  }, [searchParams])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    const { google_calendar_connected, ...payload } = form
    // Don't send empty password on edit
    const data: Record<string, string> = { ...payload }
    if (isEdit && !data.password) {
      delete data.password
    }
    if (isEdit) {
      await api.put(`/agents/${id}/`, data)
    } else {
      await api.post('/agents/', data)
    }
    setSaving(false)
    navigate('/agents')
  }

  const handleConnectGoogle = () => {
    const apiBase = import.meta.env.VITE_API_URL || '/api'
    const token = localStorage.getItem('token')
    window.location.href = `${apiBase}/google/connect/${id}/?token=${token}`
  }

  const handleDisconnectGoogle = async () => {
    if (!confirm('¿Desconectar Google Calendar de este agente?')) return
    await api.post(`/agents/${id}/disconnect-google/`)
    setForm({ ...form, google_calendar_connected: false })
    setGoogleStatus(null)
  }

  const inputClass = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent'

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        {isEdit ? 'Editar Agente' : 'Nuevo Agente'}
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4 max-w-lg">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
          <input name="name" value={form.name} onChange={handleChange} required className={inputClass} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
          <input name="phone" value={form.phone} onChange={handleChange} className={inputClass} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input name="email" type="email" value={form.email} onChange={handleChange} className={inputClass} />
        </div>

        {/* Credentials */}
        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-3">Credenciales de acceso</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Usuario *</label>
              <input
                name="username"
                value={form.username}
                onChange={handleChange}
                required
                autoComplete="off"
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contraseña {isEdit ? '' : '*'}
              </label>
              <input
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                required={!isEdit}
                autoComplete="new-password"
                placeholder={isEdit ? 'Dejar vacío para mantener actual' : ''}
                className={inputClass}
              />
            </div>
          </div>
        </div>

        {/* Google Calendar Section */}
        {isEdit && (
          <div className="border border-gray-200 rounded-lg p-4 mt-6">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Google Calendar</h3>

            {googleStatus === 'connected' && (
              <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-3 py-2 mb-3">
                Google Calendar conectado exitosamente
              </div>
            )}
            {googleStatus === 'error' && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2 mb-3">
                Error al conectar Google Calendar. Intenta de nuevo.
              </div>
            )}

            {form.google_calendar_connected ? (
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1.5 text-sm text-green-700 bg-green-50 px-3 py-1 rounded-full">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  Conectado
                </span>
                <button
                  type="button"
                  onClick={handleDisconnectGoogle}
                  className="text-red-600 hover:text-red-800 text-sm underline"
                >
                  Desconectar
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1.5 text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                  <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
                  No conectado
                </span>
                <button
                  type="button"
                  onClick={handleConnectGoogle}
                  className="bg-white border border-gray-300 text-gray-700 px-4 py-1.5 rounded-lg text-sm hover:bg-gray-50 transition-colors"
                >
                  Conectar Google Calendar
                </button>
              </div>
            )}
          </div>
        )}

        <div className="flex gap-4 pt-4">
          <button
            type="submit"
            disabled={saving}
            className="bg-indigo-600 text-white px-6 py-2 rounded-xl shadow-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Guardando...' : isEdit ? 'Actualizar' : 'Crear'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/agents')}
            className="bg-gray-200 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
