import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function PromptEditor() {
  const [tab, setTab] = useState<'editor' | 'analysis'>('editor')

  // Editor state
  const [content, setContent] = useState('')
  const [updatedAt, setUpdatedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Analysis state
  const [analysis, setAnalysis] = useState('')
  const [conversationsAnalyzed, setConversationsAnalyzed] = useState(0)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    api.get('/prompt/').then((res) => {
      setContent(res.data.content)
      setUpdatedAt(res.data.updated_at)
      setLoading(false)
    })
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      const res = await api.put('/prompt/', { content })
      setUpdatedAt(res.data.updated_at)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } finally {
      setSaving(false)
    }
  }

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setAnalysis('')
    try {
      const res = await api.post('/prompt/analyze/')
      setAnalysis(res.data.analysis)
      setConversationsAnalyzed(res.data.conversations_analyzed)
    } catch {
      setAnalysis('Error al analizar. Intenta de nuevo.')
    } finally {
      setAnalyzing(false)
    }
  }

  if (loading) return <p className="text-gray-500">Cargando prompt...</p>

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">System Prompt</h2>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setTab('editor')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'editor' ? 'bg-indigo-600 text-white shadow-sm' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Editor
        </button>
        <button
          onClick={() => setTab('analysis')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'analysis' ? 'bg-indigo-600 text-white shadow-sm' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Analisis
        </button>
      </div>

      {tab === 'editor' && (
        <div className="space-y-4">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full h-[40vh] md:h-[60vh] p-4 border border-gray-300 rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />

          <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
            <button
              onClick={handleSave}
              disabled={saving}
              className="w-full sm:w-auto px-6 py-2 bg-indigo-600 text-white rounded-xl shadow-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {saving ? 'Guardando...' : 'Guardar'}
            </button>

            {saved && (
              <span className="text-green-600 text-sm font-medium">
                Guardado correctamente
              </span>
            )}

            {updatedAt && (
              <span className="text-gray-400 text-sm">
                Ultima actualizacion: {new Date(updatedAt).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      )}

      {tab === 'analysis' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
            <p className="text-gray-600 mb-4">
              Analiza las conversaciones recientes del chatbot usando IA para obtener sugerencias de mejora al prompt actual.
            </p>

            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="px-6 py-2 bg-indigo-600 text-white rounded-xl shadow-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {analyzing ? 'Analizando...' : 'Analizar conversaciones'}
            </button>
          </div>

          {analyzing && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6 flex items-center gap-3">
              <div className="animate-spin h-5 w-5 border-2 border-indigo-600 border-t-transparent rounded-full" />
              <span className="text-gray-600">Analizando conversaciones con IA, esto puede tomar un momento...</span>
            </div>
          )}

          {analysis && !analyzing && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-semibold text-gray-900">Resultado del analisis</h3>
                <span className="text-sm text-gray-500">
                  {conversationsAnalyzed} conversaciones analizadas
                </span>
              </div>
              <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                {analysis}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
