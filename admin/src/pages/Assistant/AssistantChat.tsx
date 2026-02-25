import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../../api/client'
import ChatMessage from '../../components/ChatMessage'

interface Conversation {
  session_id: string
  created_at: string
  message_count: number
  last_message_at: string
  preview: string
  agent_name: string | null
}

interface Message {
  role: 'user' | 'assistant' | 'admin'
  content: string
  created_at: string
}

const POLL_INTERVAL = 5000

export default function AssistantChat() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const selectedIdRef = useRef<string | null>(null)

  // Search
  const [searchQuery, setSearchQuery] = useState('')
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout>>(null)

  // Admin reply
  const [replyText, setReplyText] = useState('')
  const [sending, setSending] = useState(false)

  // Pause state
  const [isPaused, setIsPaused] = useState(false)
  const [pauseRemaining, setPauseRemaining] = useState(0)

  // Scroll tracking
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const isNearBottomRef = useRef(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const fetchConversations = useCallback(async (silent = false, search = '') => {
    if (!silent) setLoading(true)
    const res = await api.get('/conversations/', { params: search ? { search } : {} })
    setConversations(res.data.results)
    if (!silent) setLoading(false)
  }, [])

  const fetchMessages = useCallback(async (sessionId: string) => {
    const res = await api.get(`/chat/${sessionId}/`)
    setMessages(res.data.messages)
    setIsPaused(!!res.data.is_ai_paused)
    setPauseRemaining(res.data.pause_remaining_seconds || 0)
  }, [])

  // Initial load
  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  // Auto-select from ?chat= query param
  useEffect(() => {
    const chatParam = searchParams.get('chat')
    if (chatParam && !selectedId) {
      selectConversation(chatParam)
      setSearchParams({}, { replace: true })
    }
  }, [searchParams]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(() => {
      fetchConversations(true, searchQuery)
      if (selectedIdRef.current) {
        fetchMessages(selectedIdRef.current)
      }
    }, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchConversations, fetchMessages, searchQuery])

  // Debounced search
  useEffect(() => {
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current)
    searchDebounceRef.current = setTimeout(() => {
      fetchConversations(true, searchQuery)
    }, 300)
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current)
    }
  }, [searchQuery, fetchConversations])

  // Auto-scroll only if near bottom
  useEffect(() => {
    if (isNearBottomRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  // Pause countdown
  useEffect(() => {
    if (pauseRemaining <= 0) return
    const interval = setInterval(() => {
      setPauseRemaining((prev) => {
        if (prev <= 1) {
          setIsPaused(false)
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [pauseRemaining])

  const handleScroll = () => {
    const el = messagesContainerRef.current
    if (!el) return
    isNearBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100
  }

  const selectConversation = async (sessionId: string) => {
    setSelectedId(sessionId)
    selectedIdRef.current = sessionId
    isNearBottomRef.current = true
    setLoadingMessages(true)
    setReplyText('')
    await fetchMessages(sessionId)
    setLoadingMessages(false)
  }

  const goBackToList = () => {
    setSelectedId(null)
    selectedIdRef.current = null
    setMessages([])
    setIsPaused(false)
    setPauseRemaining(0)
  }

  const sendAdminReply = async () => {
    if (!replyText.trim() || !selectedId || sending) return
    setSending(true)
    try {
      await api.post(`/chat/${selectedId}/reply/`, { message: replyText.trim() })
      setReplyText('')
      await fetchMessages(selectedId)
    } catch {
      // silently handle
    } finally {
      setSending(false)
    }
  }

  const unpauseAI = async () => {
    if (!selectedId) return
    await api.post(`/chat/${selectedId}/unpause/`)
    setIsPaused(false)
    setPauseRemaining(0)
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

  const formatCountdown = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="flex flex-col h-[calc(100dvh-7rem)] lg:h-[calc(100vh-4rem)]">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-900">Conversaciones</h2>
        <span className="text-xs text-gray-400 flex items-center gap-1">
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
          Actualización automática
        </span>
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">
        {/* Conversation list */}
        <div className={`w-full md:w-80 md:shrink-0 bg-white rounded-xl shadow-sm border border-gray-200/60 flex flex-col ${
          selectedId ? 'hidden md:flex' : ''
        }`}>
          {/* Search bar */}
          <div className="p-3 border-b border-gray-200 sticky top-0 bg-white rounded-t-xl z-10">
            <input
              type="text"
              placeholder="Buscar chats..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400"
            />
          </div>

          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <p className="p-4 text-gray-500">Cargando...</p>
            ) : conversations.length === 0 ? (
              <p className="p-4 text-gray-500 text-center">
                {searchQuery ? 'Sin resultados' : 'No hay conversaciones aún'}
              </p>
            ) : (
              conversations.map((conv) => (
                <button
                  key={conv.session_id}
                  onClick={() => selectConversation(conv.session_id)}
                  className={`w-full text-left p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                    selectedId === conv.session_id ? 'bg-indigo-50 border-l-4 border-l-indigo-600' : ''
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
                    <div className="flex items-center gap-1.5">
                      {conv.agent_name && (
                        <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full truncate max-w-[100px]">
                          {conv.agent_name}
                        </span>
                      )}
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                        {conv.message_count} msgs
                      </span>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Conversation detail */}
        <div className={`flex-1 bg-white rounded-xl shadow-sm border border-gray-200/60 flex flex-col overflow-hidden ${
          selectedId ? '' : 'hidden md:flex'
        }`}>
          {!selectedId ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              <p>Selecciona una conversación para ver el historial</p>
            </div>
          ) : loadingMessages ? (
            <p className="p-4 text-gray-500">Cargando mensajes...</p>
          ) : (
            <>
              {/* Fixed header */}
              <div className="px-4 py-3 md:px-6 md:py-4 border-b border-gray-200 shrink-0">
                <div className="flex items-center justify-between relative z-10">
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

                {/* Pause indicator */}
                {isPaused && (
                  <div className="mt-2 flex items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-amber-100 text-amber-700 rounded-full">
                      <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse" />
                      IA pausada — {formatCountdown(pauseRemaining)}
                    </span>
                    <button
                      onClick={unpauseAI}
                      className="px-2.5 py-1 text-xs font-medium text-amber-700 hover:bg-amber-50 rounded-full transition-colors"
                    >
                      Reanudar
                    </button>
                  </div>
                )}
              </div>

              {/* Scrollable messages */}
              <div
                ref={messagesContainerRef}
                onScroll={handleScroll}
                className="flex-1 overflow-y-auto px-4 py-4 md:px-6"
              >
                {messages.map((msg, i) => (
                  <ChatMessage key={i} role={msg.role} content={msg.content} />
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* Fixed input */}
              <div className="px-4 py-3 md:px-6 md:py-4 border-t border-gray-200 shrink-0">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        sendAdminReply()
                      }
                    }}
                    placeholder="Responder como admin..."
                    className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400"
                  />
                  <button
                    onClick={sendAdminReply}
                    disabled={!replyText.trim() || sending}
                    className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {sending ? '...' : 'Enviar'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
