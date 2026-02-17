interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
}

function parseContent(content: string) {
  const mediaRegex = /\[media:(image|video)\](.*?)\[\/media\]/g
  const parts: Array<{ type: 'text'; value: string } | { type: 'image'; url: string } | { type: 'video'; url: string }> = []
  let lastIndex = 0
  let match

  while ((match = mediaRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      const text = content.slice(lastIndex, match.index).trim()
      if (text) parts.push({ type: 'text', value: text })
    }
    if (match[1] === 'image') {
      parts.push({ type: 'image', url: match[2] })
    } else {
      parts.push({ type: 'video', url: match[2] })
    }
    lastIndex = match.index + match[0].length
  }

  const remaining = content.slice(lastIndex).trim()
  if (remaining) parts.push({ type: 'text', value: remaining })

  return parts
}

export default function ChatMessage({ role, content }: ChatMessageProps) {
  const isUser = role === 'user'
  const parts = parseContent(content)

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-sm'
            : 'bg-gray-200 text-gray-900 rounded-bl-sm'
        }`}
      >
        {parts.map((part, i) => {
          if (part.type === 'text') {
            return <p key={i} className="text-sm whitespace-pre-wrap">{part.value}</p>
          }
          if (part.type === 'image') {
            return <img key={i} src={part.url} alt="" className="rounded-lg mt-2 max-w-full max-h-48 object-cover" />
          }
          if (part.type === 'video') {
            return <video key={i} src={part.url} controls className="rounded-lg mt-2 max-w-full max-h-48" />
          }
          return null
        })}
      </div>
    </div>
  )
}
