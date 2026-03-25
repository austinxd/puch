import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../../api/client'

interface PropertyImage {
  id: number
  image: string
  order: number
}

interface PropertyVideo {
  id: number
  video: string
}

interface Prohibicion {
  id: number
  nombre: string
}

interface Property {
  id: number
  identificador: string
  nombre: string
  clase: string
  operacion: string
  distrito: string
  calle: string
  direccion: string
  referencia: string
  precio: string | null
  moneda: string
  metraje: string
  habitaciones: string
  banos: string
  cocheras: string
  piso: string
  vista: string
  distribucion: string
  pitch: string
  antiguedad: string
  ascensor: string
  cantidad_pisos: string
  tipo_cocina: string
  terraza_balcon: string
  cuarto_servicio: string
  bano_servicio: string
  costo_mantenimiento: string
  tipologia: string
  documentacion: string
  parametros_usos: string
  financiamiento: string
  link_maps: string
  images: PropertyImage[]
  videos: PropertyVideo[]
  recorrido_360: string
  prohibiciones_detail: Prohibicion[]
  activo: boolean
  agent_name: string
  agent: number | null
}

function InfoRow({ label, value }: { label: string; value: string | null }) {
  if (!value) return null
  return (
    <div className="py-2 flex">
      <dt className="w-48 text-sm font-medium text-gray-500 shrink-0">{label}</dt>
      <dd className="text-sm text-gray-900">{value}</dd>
    </div>
  )
}

function MediaGallery({ images, videos, recorrido360 }: { images: string[]; videos: PropertyVideo[]; recorrido360: string }) {
  const [open, setOpen] = useState(false)
  const totalCount = images.length + videos.length + (recorrido360 ? 1 : 0)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 mb-8 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900">Medios</h3>
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{totalCount}</span>
        </div>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4">
          {images.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {images.map((url, i) => (
                <img key={i} src={url} alt={`Imagen ${i + 1}`} className="rounded-lg object-cover w-full h-48" />
              ))}
            </div>
          )}

          {videos[0] && (
            <video src={videos[0].video} controls className="rounded-lg max-h-64 w-full" />
          )}

          {recorrido360 && (
            <a href={recorrido360} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline text-sm block">
              Recorrido 360
            </a>
          )}
        </div>
      )}
    </div>
  )
}

export default function PropertyDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [property, setProperty] = useState<Property | null>(null)

  useEffect(() => {
    api.get(`/properties/${id}/`).then((res) => setProperty(res.data))
  }, [id])

  if (!property) return <p className="text-gray-500">Cargando...</p>

  const images = property.images.map((i) => i.image)

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{property.nombre}</h2>
          <p className="text-gray-500">{property.identificador}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate(`/properties/${id}/edit`)}
            className="bg-indigo-600 text-white px-4 py-2 rounded-xl shadow-sm hover:bg-indigo-700 transition-colors"
          >
            Editar
          </button>
          <button
            onClick={() => navigate('/properties')}
            className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Volver
          </button>
        </div>
      </div>

      {(images.length > 0 || property.videos.length > 0 || property.recorrido_360) && (
        <MediaGallery images={images} videos={property.videos} recorrido360={property.recorrido_360} />
      )}

      {property.pitch && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-indigo-900">{property.pitch}</p>
        </div>
      )}

      {property.prohibiciones_detail?.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Prohibiciones</h3>
          <div className="flex flex-wrap gap-2">
            {property.prohibiciones_detail.map((p) => (
              <span key={p.id} className="inline-flex items-center bg-red-100 text-red-800 text-sm px-3 py-1 rounded-full">
                {p.nombre}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Información General</h3>
          <dl className="divide-y divide-gray-100">
            <InfoRow label="Clase" value={property.clase} />
            <InfoRow label="Operación" value={property.operacion} />
            <InfoRow label="Tipología" value={property.tipologia} />
            <InfoRow label="Precio" value={property.precio ? `${property.moneda === 'PEN' ? 'S/' : '$'}${Number(property.precio).toLocaleString()}` : null} />
            <InfoRow label="Agente" value={property.agent_name} />
            <InfoRow label="Antigüedad" value={property.antiguedad} />
            <InfoRow label="Costo Mant." value={property.costo_mantenimiento} />
            <InfoRow label="Estado" value={property.activo ? 'Activo' : 'Inactivo'} />
          </dl>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Ubicación</h3>
          <dl className="divide-y divide-gray-100">
            <InfoRow label="Distrito" value={property.distrito} />
            <InfoRow label="Calle" value={property.calle} />
            <InfoRow label="Dirección" value={property.direccion} />
            <InfoRow label="Referencia" value={property.referencia} />
            {property.link_maps && (
              <div className="py-2">
                <a href={property.link_maps} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline text-sm">
                  Ver en Google Maps
                </a>
              </div>
            )}
          </dl>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Características</h3>
          <dl className="divide-y divide-gray-100">
            <InfoRow label="Metraje" value={property.metraje} />
            <InfoRow label="Habitaciones" value={property.habitaciones} />
            <InfoRow label="Baños" value={property.banos} />
            <InfoRow label="Cocheras" value={property.cocheras} />
            <InfoRow label="Piso" value={property.piso} />
            <InfoRow label="Cant. Pisos" value={property.cantidad_pisos} />
            <InfoRow label="Vista" value={property.vista} />
            <InfoRow label="Ascensor" value={property.ascensor} />
            <InfoRow label="Tipo Cocina" value={property.tipo_cocina} />
            <InfoRow label="Terraza/Balcón" value={property.terraza_balcon} />
            <InfoRow label="Cuarto Servicio" value={property.cuarto_servicio} />
            <InfoRow label="Baño Servicio" value={property.bano_servicio} />
          </dl>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Distribución</h3>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{property.distribucion || 'No especificada'}</p>
        </div>
      </div>

      {(property.documentacion || property.parametros_usos || property.financiamiento) && (
        <div className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Documentación y Financiamiento</h3>
          <dl className="space-y-4">
            {property.documentacion && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Documentación</dt>
                <dd className="text-sm text-gray-900 mt-1 whitespace-pre-wrap">{property.documentacion}</dd>
              </div>
            )}
            {property.parametros_usos && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Parámetros / Usos</dt>
                <dd className="text-sm text-gray-900 mt-1 whitespace-pre-wrap">{property.parametros_usos}</dd>
              </div>
            )}
            {property.financiamiento && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Financiamiento</dt>
                <dd className="text-sm text-gray-900 mt-1 whitespace-pre-wrap">{property.financiamiento}</dd>
              </div>
            )}
          </dl>
        </div>
      )}

      {/* Videos and recorrido moved into MediaGallery above */}
    </div>
  )
}
