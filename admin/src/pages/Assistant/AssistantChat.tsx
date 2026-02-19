import { useState, useEffect, useRef, useCallback } from 'react'
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

const POLL_INTERVAL = 5000 // 5 seconds

export default function AssistantChat() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const selectedIdRef = useRef<string | null>(null)

  const fetchConversations = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    const res = await api.get('/conversations/')
    setConversations(res.data.results)
    if (!silent) setLoading(false)
  }, [])

  const fetchMessages = useCallback(async (sessionId: string) => {
    const res = await api.get(`/chat/${sessionId}/`)
    setMessages(res.data.messages)
  }, [])

  // Initial load
  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  // Auto-refresh conversations and selected chat
  useEffect(() => {
    const interval = setInterval(() => {
      fetchConversations(true)
      if (selectedIdRef.current) {
        fetchMessages(selectedIdRef.current)
      }
    }, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchConversations, fetchMessages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const selectConversation = async (sessionId: string) => {
    setSelectedId(sessionId)
    selectedIdRef.current = sessionId
    setLoadingMessages(true)
    await fetchMessages(sessionId)
    setLoadingMessages(false)
  }

  const goBackToList = () => {
    setSelectedId(null)
    selectedIdRef.current = null
    setMessages([])
  }

  const isPhone = (id: string) => /^\d{7,15}$/.test(id)

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
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-900">Conversaciones</h2>
        <span className="text-xs text-gray-400 flex items-center gap-1">
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
          Actualización automática
        </span>
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">
        {/* Lista de conversaciones */}
        <div className={`w-full md:w-80 md:shrink-0 bg-white rounded-lg shadow overflow-y-auto ${
          selectedId ? 'hidden md:block' : ''
        }`}>
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
                {isPhone(conv.session_id) && (
                  <p className="text-xs text-green-600 font-medium mb-1">
                    +{conv.session_id}
                  </p>
                )}
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
        <div className={`flex-1 bg-white rounded-lg shadow p-4 md:p-6 overflow-y-auto ${
          selectedId ? '' : 'hidden md:block'
        }`}>
          {!selectedId ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              <p>Selecciona una conversación para ver el historial</p>
            </div>
          ) : loadingMessages ? (
            <p className="text-gray-500">Cargando mensajes...</p>
          ) : (
            <>
              <div className="mb-4 pb-3 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <button
                    onClick={goBackToList}
                    className="md:hidden p-1 text-gray-500 hover:text-gray-700"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                  </button>
                  <p className="text-xs text-gray-500">
                    {isPhone(selectedId) ? `+${selectedId}` : `Sesión: ${selectedId.slice(0, 8)}`}
                  </p>
                </div>
                {isPhone(selectedId) && (
                  <div className="flex gap-2">
                    <a
                      href={`https://wa.me/${selectedId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full hover:bg-green-200 transition-colors"
                    >
                      WhatsApp
                    </a>
                    <a
                      href={`tel:+${selectedId}`}
                      className="px-3 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
                    >
                      Llamar
                    </a>
                  </div>
                )}
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
