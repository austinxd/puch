import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../../api/client'

interface Agent {
  id: number
  name: string
}

const INITIAL = {
  identificador: '',
  clase: 'Residencial',
  agent: '',
  nombre: '',
  tipologia: '',
  operacion: 'Venta',
  link_maps: '',
  distrito: '',
  pitch: '',
  calle: '',
  direccion: '',
  referencia: '',
  antiguedad: '',
  precio: '',
  costo_mantenimiento: '',
  metraje: '',
  vista: '',
  distribucion: '',
  ascensor: '',
  habitaciones: '',
  cocheras: '',
  cantidad_pisos: '',
  tipo_cocina: '',
  terraza_balcon: '',
  piso: '',
  banos: '',
  cuarto_servicio: '',
  bano_servicio: '',
  documentacion: '',
  parametros_usos: '',
  financiamiento: '',
  imagen_1: '',
  imagen_2: '',
  imagen_3: '',
  imagen_4: '',
  imagen_5: '',
  video: '',
  recorrido_360: '',
  activo: true,
}

type FormData = typeof INITIAL

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  )
}

const inputClass = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent'

export default function PropertyForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<FormData>(INITIAL)
  const [agents, setAgents] = useState<Agent[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get('/agents/').then((res) => setAgents(res.data.results))
    if (isEdit) {
      api.get(`/properties/${id}/`).then((res) => {
        const d = res.data
        setForm({
          ...INITIAL,
          ...d,
          agent: d.agent ?? '',
          precio: d.precio ?? '',
        })
      })
    }
  }, [id])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    const payload = {
      ...form,
      agent: form.agent || null,
      precio: form.precio || null,
    }
    if (isEdit) {
      await api.put(`/properties/${id}/`, payload)
    } else {
      await api.post('/properties/', payload)
    }
    setSaving(false)
    navigate('/properties')
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        {isEdit ? 'Editar Propiedad' : 'Nueva Propiedad'}
      </h2>
      <form onSubmit={handleSubmit} className="space-y-8 max-w-4xl">
        {/* Info Básica */}
        <section>
          <h3 className="text-lg font-semibold text-gray-800 mb-4 border-b pb-2">Información Básica</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="Identificador *">
              <input name="identificador" value={form.identificador} onChange={handleChange} required className={inputClass} />
            </Field>
            <Field label="Nombre *">
              <input name="nombre" value={form.nombre} onChange={handleChange} required className={inputClass} />
            </Field>
            <Field label="Clase">
              <select name="clase" value={form.clase} onChange={handleChange} className={inputClass}>
                <option value="Residencial">Residencial</option>
                <option value="Comercial">Comercial</option>
                <option value="Industrial">Industrial</option>
              </select>
            </Field>
            <Field label="Operación">
              <select name="operacion" value={form.operacion} onChange={handleChange} className={inputClass}>
                <option value="Venta">Venta</option>
                <option value="Alquiler">Alquiler</option>
              </select>
            </Field>
            <Field label="Tipología">
              <input name="tipologia" value={form.tipologia} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Agente">
              <select name="agent" value={form.agent} onChange={handleChange} className={inputClass}>
                <option value="">Sin agente</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Precio">
              <input name="precio" type="number" step="0.01" value={form.precio} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Antigüedad">
              <input name="antiguedad" value={form.antiguedad} onChange={handleChange} className={inputClass} />
            </Field>
            <div className="flex items-end">
              <label className="flex items-center gap-2">
                <input type="checkbox" name="activo" checked={form.activo} onChange={handleChange} className="rounded" />
                <span className="text-sm text-gray-700">Activo</span>
              </label>
            </div>
          </div>
          <div className="mt-4">
            <Field label="Pitch">
              <textarea name="pitch" value={form.pitch} onChange={handleChange} rows={3} className={inputClass} />
            </Field>
          </div>
        </section>

        {/* Ubicación */}
        <section>
          <h3 className="text-lg font-semibold text-gray-800 mb-4 border-b pb-2">Ubicación</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="Distrito">
              <input name="distrito" value={form.distrito} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Calle">
              <input name="calle" value={form.calle} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Dirección">
              <input name="direccion" value={form.direccion} onChange={handleChange} className={inputClass} />
            </Field>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <Field label="Referencia">
              <textarea name="referencia" value={form.referencia} onChange={handleChange} rows={2} className={inputClass} />
            </Field>
            <Field label="Link Maps">
              <input name="link_maps" value={form.link_maps} onChange={handleChange} className={inputClass} />
            </Field>
          </div>
        </section>

        {/* Características */}
        <section>
          <h3 className="text-lg font-semibold text-gray-800 mb-4 border-b pb-2">Características</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Field label="Metraje">
              <input name="metraje" value={form.metraje} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Habitaciones">
              <input name="habitaciones" value={form.habitaciones} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Baños">
              <input name="banos" value={form.banos} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Cocheras">
              <input name="cocheras" value={form.cocheras} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Piso">
              <input name="piso" value={form.piso} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Cantidad Pisos">
              <input name="cantidad_pisos" value={form.cantidad_pisos} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Vista">
              <input name="vista" value={form.vista} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Ascensor">
              <input name="ascensor" value={form.ascensor} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Tipo Cocina">
              <input name="tipo_cocina" value={form.tipo_cocina} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Terraza/Balcón">
              <input name="terraza_balcon" value={form.terraza_balcon} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Cuarto de Servicio">
              <input name="cuarto_servicio" value={form.cuarto_servicio} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Baño de Servicio">
              <input name="bano_servicio" value={form.bano_servicio} onChange={handleChange} className={inputClass} />
            </Field>
            <Field label="Costo Mantenimiento">
              <input name="costo_mantenimiento" value={form.costo_mantenimiento} onChange={handleChange} className={inputClass} />
            </Field>
          </div>
          <div className="mt-4">
            <Field label="Distribución">
              <textarea name="distribucion" value={form.distribucion} onChange={handleChange} rows={3} className={inputClass} />
            </Field>
          </div>
        </section>

        {/* Medios */}
        <section>
          <h3 className="text-lg font-semibold text-gray-800 mb-4 border-b pb-2">Medios</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4, 5].map((n) => (
              <Field key={n} label={`Imagen ${n}`}>
                <input
                  name={`imagen_${n}`}
                  value={(form as Record<string, unknown>)[`imagen_${n}`] as string}
                  onChange={handleChange}
                  placeholder="URL de la imagen"
                  className={inputClass}
                />
              </Field>
            ))}
            <Field label="Video">
              <input name="video" value={form.video} onChange={handleChange} placeholder="URL del video" className={inputClass} />
            </Field>
            <Field label="Recorrido 360">
              <input name="recorrido_360" value={form.recorrido_360} onChange={handleChange} placeholder="URL recorrido 360" className={inputClass} />
            </Field>
          </div>
        </section>

        {/* Documentación */}
        <section>
          <h3 className="text-lg font-semibold text-gray-800 mb-4 border-b pb-2">Documentación y Financiamiento</h3>
          <div className="grid grid-cols-1 gap-4">
            <Field label="Documentación">
              <textarea name="documentacion" value={form.documentacion} onChange={handleChange} rows={3} className={inputClass} />
            </Field>
            <Field label="Parámetros / Usos">
              <textarea name="parametros_usos" value={form.parametros_usos} onChange={handleChange} rows={3} className={inputClass} />
            </Field>
            <Field label="Financiamiento">
              <textarea name="financiamiento" value={form.financiamiento} onChange={handleChange} rows={3} className={inputClass} />
            </Field>
          </div>
        </section>

        <div className="flex gap-4">
          <button
            type="submit"
            disabled={saving}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Guardando...' : isEdit ? 'Actualizar' : 'Crear'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/properties')}
            className="bg-gray-200 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
