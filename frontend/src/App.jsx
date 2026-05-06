import { useState, useRef, useEffect } from 'react'

const API = 'http://localhost:8000'

function renderText(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : part.split('\n').map((line, j, arr) => (
          <span key={`${i}-${j}`}>{line}{j < arr.length - 1 ? <br /> : null}</span>
        ))
  )
}

export default function App() {
  const [messages, setMessages]   = useState([])
  const [input, setInput]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)
  const [expanded, setExpanded]   = useState({})
  const bottomRef                 = useRef(null)
  const inputRef                  = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return

    setInput('')
    setError(null)

    const userMsg = { role: 'user', text, id: Date.now() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })

      if (!res.ok) throw new Error(`Server error: ${res.status}`)

      const data = await res.json()
      const botMsg = {
        role: 'bot',
        text: data.reply,
        sources: data.sources || [],
        id: Date.now() + 1,
      }
      setMessages(prev => [...prev, botMsg])
    } catch (err) {
      setError('Could not reach the server. Is the backend running on port 8000?')
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChat = async () => {
    setMessages([])
    setError(null)
    setExpanded({})
    try { await fetch(`${API}/history`, { method: 'DELETE' }) } catch (_) {}
    inputRef.current?.focus()
  }

  const toggleSources = (id) =>
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }))

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <div className="status-dot" />
          <div>
            <h1>DND 5e GUIDE</h1>
          </div>
        </div>
        <button className="clear-btn" onClick={clearChat}>clear</button>
      </header>

      <main className="messages">
        {messages.length === 0 && !loading && (
          <div className="welcome">
            <span className="welcome-icon">⚔️</span>
            <h2>// tavern board</h2>
            <p>
              Ask about any D&amp;D 5e SRD class.<br />
              Try: <em>"tell me about the wizard"</em>,<br />
              <em>"does the paladin cast spells?"</em>,<br />
              or <em>"what subclasses does the druid have?"</em>
            </p>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={`bubble-wrap ${msg.role}`}>
            <div className="bubble-label">
              {msg.role === 'user' ? 'you' : 'groq · llama-3.3'}
            </div>
            <div className={`bubble ${msg.role}`}>
              {msg.role === 'bot' ? renderText(msg.text) : msg.text}
            </div>

            {/* RAG sources toggle */}
            {msg.role === 'bot' && msg.sources?.length > 0 && (
              <div className="sources-wrap">
                <button
                  className="sources-toggle"
                  onClick={() => toggleSources(msg.id)}
                >
                  {expanded[msg.id] ? '▾' : '▸'} {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''} retrieved
                </button>
                {expanded[msg.id] && (
                  <div className="sources-list">
                    {msg.sources.map((s, i) => (
                      <div key={i} className="source-item">{s}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="bubble-wrap bot">
            <div className="bubble-label">groq · llama-3.3</div>
            <div className="typing"><span /><span /><span /></div>
          </div>
        )}

        {error && <div className="error">⚠ {error}</div>}
        <div ref={bottomRef} />
      </main>

      <div className="input-area">
        <span className="prompt-label">&gt;_</span>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="ask about a class..."
          disabled={loading}
          autoFocus
        />
        <button
          className="send-btn"
          onClick={sendMessage}
          disabled={!input.trim() || loading}
        >
          send ↵
        </button>
      </div>
    </div>
  )
}