import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../../api/client'

interface ProfileData {
  id: number
  name: string
  phone: string
  email: string
  google_calendar_connected: boolean
}

export default function MyProfile() {
  const [searchParams] = useSearchParams()
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [form, setForm] = useState({ name: '', phone: '', email: '' })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [googleStatus, setGoogleStatus] = useState<string | null>(null)

  const fetchProfile = () => {
    api.get('/auth/profile/').then((res) => {
      setProfile(res.data)
      setForm({ name: res.data.name, phone: res.data.phone, email: res.data.email })
    })
  }

  useEffect(() => {
    fetchProfile()
  }, [])

  useEffect(() => {
    const googleParam = searchParams.get('google')
    if (googleParam === 'connected') {
      setGoogleStatus('connected')
      fetchProfile()
    } else if (googleParam === 'error') {
      setGoogleStatus('error')
    }
  }, [searchParams])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value })
    setSaved(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    await api.patch('/auth/profile/', form)
    setSaving(false)
    setSaved(true)
  }

  const handleConnectGoogle = () => {
    if (!profile) return
    const apiBase = import.meta.env.VITE_API_URL || '/api'
    const token = localStorage.getItem('token')
    window.location.href = `${apiBase}/google/connect/${profile.id}/?source=profile&token=${token}`
  }

  const handleDisconnectGoogle = async () => {
    if (!profile) return
    if (!confirm('¿Desconectar Google Calendar?')) return
    await api.post(`/agents/${profile.id}/disconnect-google/`)
    setProfile({ ...profile, google_calendar_connected: false })
    setGoogleStatus(null)
  }

  if (!profile) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    )
  }

  const inputClass = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent'

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Mi Perfil</h2>

      <form onSubmit={handleSubmit} className="space-y-4 max-w-lg">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
          <input name="name" value={form.name} onChange={handleChange} className={inputClass} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
          <input name="phone" value={form.phone} onChange={handleChange} className={inputClass} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input name="email" type="email" value={form.email} onChange={handleChange} className={inputClass} />
        </div>

        <div className="flex items-center gap-4 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="bg-indigo-600 text-white px-6 py-2 rounded-xl shadow-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Guardando...' : 'Guardar'}
          </button>
          {saved && (
            <span className="text-green-600 text-sm">Guardado correctamente</span>
          )}
        </div>
      </form>

      {/* Google Calendar */}
      <div className="border border-gray-200 rounded-lg p-4 mt-8 max-w-lg">
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

        {profile.google_calendar_connected ? (
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
    </div>
  )
}
