import api from './client'

export interface PropertySummary {
  id: number
  identificador: string
  nombre: string
  distrito: string
  tipologia: string
  precio: string | null
  moneda: string
  image_url: string | null
}

export interface IntentSummary {
  operacion: string
  tipo_propiedad: string
  distritos: string
  precio_min: string | null
  precio_max: string | null
  habitaciones: string
  caracteristicas: string
  resumen: string
  updated_at: string
}

export interface ClientListItem {
  phone: string
  phone_display: string
  conversation_count: number
  message_count: number
  last_activity: string
  first_property: PropertySummary | null
  interested_count: number
  latest_intent: IntentSummary
}

export interface ClientConversation {
  session_id: string
  created_at: string
  last_message_at: string | null
  message_count: number
  agent_name: string | null
  first_property: PropertySummary | null
}

export interface InterestedProperty {
  property: PropertySummary
  first_shown_at: string
  last_shown_at: string
  shown_count: number
  session_ids: string[]
}

export interface ClientDetail {
  phone: string
  phone_display: string
  latest_intent: (IntentSummary & { id: number; session_id: string; created_at: string }) | null
  intents: Array<IntentSummary & { id: number; session_id: string; created_at: string }>
  conversations: ClientConversation[]
  interested_properties: InterestedProperty[]
}

export async function listClients(search?: string): Promise<ClientListItem[]> {
  const res = await api.get('/clients/', { params: search ? { search } : {} })
  return res.data.results
}

export async function getClient(phone: string): Promise<ClientDetail> {
  const res = await api.get(`/clients/${phone}/`)
  return res.data
}
