import { useState, useEffect, useRef } from 'react'
import api from '../../api/client'
import ChatMessage from '../../components/ChatMessage'

interface Conversation {
  session_id: string
  created_at: string
  message_count: number
  last_message_at: string
  preview: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export default function AssistantChat() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const fetchConversations = async () => {
    setLoading(true)
    const res = await api.get('/conversations/')
    setConversations(res.data.results)
    setLoading(false)
  }

  const selectConversation = async (sessionId: string) => {
    setSelectedId(sessionId)
    setLoadingMessages(true)
    const res = await api.get(`/chat/${sessionId}/`)
    setMessages(res.data.messages)
    setLoadingMessages(false)
  }

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr)
    return d.toLocaleDateString('es-PE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Conversaciones</h2>

      <div className="flex flex-1 gap-4 overflow-hidden">
        {/* Lista de conversaciones */}
        <div className="w-80 shrink-0 bg-white rounded-lg shadow overflow-y-auto">
          {loading ? (
            <p className="p-4 text-gray-500">Cargando...</p>
          ) : conversations.length === 0 ? (
            <p className="p-4 text-gray-500 text-center">No hay conversaciones aún</p>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.session_id}
                onClick={() => selectConversation(conv.session_id)}
                className={`w-full text-left p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                  selectedId === conv.session_id ? 'bg-blue-50 border-l-4 border-l-blue-600' : ''
                }`}
              >
                <p className="text-sm text-gray-900 font-medium truncate">
                  {conv.preview || 'Sin mensaje'}
                </p>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-xs text-gray-500">
                    {formatDate(conv.last_message_at)}
                  </span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                    {conv.message_count} msgs
                  </span>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Detalle de conversación */}
        <div className="flex-1 bg-white rounded-lg shadow p-6 overflow-y-auto">
          {!selectedId ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              <p>Selecciona una conversación para ver el historial</p>
            </div>
          ) : loadingMessages ? (
            <p className="text-gray-500">Cargando mensajes...</p>
          ) : (
            <>
              <div className="mb-4 pb-3 border-b border-gray-200">
                <p className="text-xs text-gray-500">Sesión: {selectedId}</p>
              </div>
              {messages.map((msg, i) => (
                <ChatMessage key={i} role={msg.role} content={msg.content} />
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
