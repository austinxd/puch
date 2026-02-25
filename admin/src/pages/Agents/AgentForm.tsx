import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../../api/client'

interface AgentFormData {
  name: string
  phone: string
  email: string
  username: string
  password: string
  google_calendar_id: string
}

export default function AgentForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<AgentFormData>({ name: '', phone: '', email: '', username: '', password: '', google_calendar_id: '' })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isEdit) {
      api.get(`/agents/${id}/`).then((res) => setForm({ ...res.data, password: '' }))
    }
  }, [id])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    const { ...payload } = form
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
        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-3">Google Calendar</h3>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Gmail del agente
            </label>
            <input
              name="google_calendar_id"
              type="email"
              value={form.google_calendar_id}
              onChange={handleChange}
              placeholder="agente@gmail.com"
              className={inputClass}
            />
            <p className="text-xs text-gray-500 mt-1">
              El agente debe compartir su Google Calendar con la cuenta de servicio de Brikia.
            </p>
          </div>
          {form.google_calendar_id ? (
            <div className="mt-3">
              <span className="inline-flex items-center gap-1.5 text-sm text-green-700 bg-green-50 px-3 py-1 rounded-full">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                Configurado
              </span>
            </div>
          ) : (
            <div className="mt-3">
              <span className="inline-flex items-center gap-1.5 text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
                No configurado
              </span>
            </div>
          )}
        </div>

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
