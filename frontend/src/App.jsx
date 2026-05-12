import { useState, useRef, useEffect } from 'react'
import SiriOrb from './SiriOrb'
import TopicDiagram from './TopicDiagram'
import './App.css'

/* ── Empty state ─────────────────────────────────────────────────────────── */
function EmptyState() {
  const topics = ['Digestive System', 'Photosynthesis', 'Human Eye', 'Water Cycle', 'Food Chain']
  return (
    <div className="empty-state">
      <div className="empty-icon">🔬</div>
      <h2 className="empty-title">Topic Explorer</h2>
      <p className="empty-sub">
        Ask Vidya about a science topic and the full diagram and explanation will appear here.
      </p>
      <div className="topic-chips">
        {topics.map(t => <span key={t} className="topic-chip">{t}</span>)}
      </div>
    </div>
  )
}

/* ── Info panel ──────────────────────────────────────────────────────────── */
function InfoPanel({ data }) {
  return (
    <div className="info-panel">

      {/* Header */}
      <div className="info-header">
        <div className="info-meta">
          {data.class   && <span className="badge">{data.class}</span>}
          {data.subject && <span className="badge badge--cyan">{data.subject}</span>}
        </div>
        <h1 className="info-topic">{data.topic}</h1>
      </div>

      {/* Diagram */}
      <TopicDiagram topic={data.topic} keywords={data.keywords ?? []} />

      {/* Overview */}
      {data.overview && (
        <div className="glass-card overview-card">
          <h3 className="card-label">Overview</h3>
          <p className="overview-text">{data.overview}</p>
        </div>
      )}

      {/* Components */}
      {data.components?.length > 0 && (
        <section className="info-section">
          <h3 className="section-heading"><span>⚙️</span> Components</h3>
          <div className="components-grid">
            {data.components.map((c, i) => (
              <div key={i} className="component-card glass-card"
                   style={{ animationDelay: `${i * 55}ms` }}>
                <div className="comp-index">{String(i + 1).padStart(2, '0')}</div>
                <div className="comp-body">
                  <h4 className="comp-name">{c.name}</h4>
                  {c.location && (
                    <p className="comp-location">
                      <span aria-hidden="true">📍</span>{c.location}
                    </p>
                  )}
                  <p className="comp-function">{c.function}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Process flow */}
      {data.process_flow?.length > 0 && (
        <section className="info-section">
          <h3 className="section-heading"><span>🔄</span> Process Flow</h3>
          <ol className="flow-list">
            {data.process_flow.map((step, i) => (
              <li key={i} className="flow-step" style={{ animationDelay: `${i * 70}ms` }}>
                <div className="flow-number">{step.step ?? i + 1}</div>
                <p className="flow-desc">{step.description}</p>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* Key facts */}
      {data.key_facts?.length > 0 && (
        <section className="info-section">
          <h3 className="section-heading"><span>💡</span> Key Facts</h3>
          <ul className="facts-list">
            {data.key_facts.map((fact, i) => (
              <li key={i} className="fact-item">
                <span className="fact-bullet" aria-hidden="true">✦</span>
                <span>{fact}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

    </div>
  )
}

/* ── Root App ────────────────────────────────────────────────────────────── */
export default function App() {
  const [messages,  setMessages]  = useState([])
  const [topicData, setTopicData] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleResult({ transcription, response, language, topicData: td }) {
    setMessages(prev => [
      ...prev,
      { role: 'user',      text: transcription, lang: language },
      { role: 'assistant', text: response,       lang: language },
    ])
    if (td) setTopicData(td)
  }

  return (
    <div className="app">

      <header className="app-header">
        <div className="logo-pill">
          <span className="logo-dot" />
          <span className="logo-name">Vidya</span>
        </div>
        <p className="app-subtitle">Multilingual Voice Learning Assistant</p>
      </header>

      <div className="app-body">

        {/* ── Left: orb + conversation ── */}
        <aside className="left-panel">
          <SiriOrb onResult={handleResult} />

          {messages.length === 0 ? (
            <p className="hint">
              Ask about <em>digestive system</em>, <em>photosynthesis</em>,{' '}
              <em>human eye</em>, <em>water cycle</em>, or <em>food chain</em>
              {' '}— in English, Hindi, or Marathi.
            </p>
          ) : (
            <div className="chat-scroll">
              {messages.map((msg, i) => (
                <div key={i} className={`bubble bubble--${msg.role}`}>
                  <span className="bubble-role">{msg.role === 'user' ? 'You' : 'Vidya'}</span>
                  <p className="bubble-text">{msg.text}</p>
                  {msg.lang && <span className="bubble-lang">{msg.lang}</span>}
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </aside>

        {/* ── Right: topic panel ── */}
        <section className="right-panel">
          {topicData ? <InfoPanel data={topicData} /> : <EmptyState />}
        </section>

      </div>
    </div>
  )
}
