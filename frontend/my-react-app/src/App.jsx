import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './App.css'

const Icon = ({ name, size = 20 }) => {
  const paths = {
    spark: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-2-5.8L4 11l6-2.2L12 3Z" /><path d="m19 14 .9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14Z" /></>,
    chart: <><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-5 5" /></>,
    upload: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m17 8-5-5-5 5M12 3v12" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    send: <><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M8 13h8M8 17h8" /></>,
    rows: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 10h18M9 4v16" /></>,
    chevron: <path d="m9 18 6-6-6-6" />,
    close: <><path d="m18 6-12 12M6 6l12 12" /></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
    sparkleSmall: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" /><path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z" /></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

function App() {
  const [file, setFile] = useState(null)
  const [summary, setSummary] = useState(null)
  const [query, setQuery] = useState('')
  const [chatHistory, setChatHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const chatEndRef = useRef(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory, loading])

  const handleUpload = async () => {
    if (!file) {
      setError('Choose a CSV or Excel file to get started.')
      return
    }
    const formData = new FormData()
    formData.append('file', file)
    setUploading(true)
    setError('')
    try {
      const res = await fetch('http://localhost:5000/api/upload', { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Upload failed. Please try again.')
      setSummary(data.summary)
      setChatHistory([])
      setFile(null)
    } catch (err) {
      setError(err.message || 'Could not connect to the backend server.')
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteDataset = async () => {
    setError('')
    try {
      const res = await fetch('http://localhost:5000/api/upload', { method: 'DELETE' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Could not delete the dataset.')
      setSummary(null)
      setChatHistory([])
      setQuery('')
      setFile(null)
    } catch (err) {
      setError(err.message || 'Could not connect to the backend server.')
    }
  }

  const handleQuerySubmit = async (e, suggestedQuery) => {
    e?.preventDefault()
    const userText = (suggestedQuery || query).trim()
    if (!userText || loading) return
    if (!summary) {
      setError('Upload a dataset first, then ask a question about it.')
      return
    }
    setQuery('')
    setError('')
    setChatHistory((prev) => [...prev, { role: 'user', content: userText }])
    setLoading(true)
    try {
      const res = await fetch('http://localhost:5000/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userText }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'The query could not be completed.')
      setChatHistory((prev) => [...prev, { role: 'assistant', content: data.result }])
    } catch (err) {
      setChatHistory((prev) => [...prev, { role: 'assistant', content: `Something went wrong: ${err.message || 'Network request failed.'}` }])
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateReport = async () => {
    if (!summary || loading) return
    setError('')
    setLoading(true)
    setSidebarOpen(false)
    setChatHistory((prev) => [...prev, { role: 'user', content: 'Generate a complete data analysis report.' }])
    try {
      const res = await fetch('http://localhost:5000/api/analyze', { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'The report could not be generated.')
      setChatHistory((prev) => [...prev, { role: 'assistant', content: data.report }])
    } catch (err) {
      setChatHistory((prev) => [...prev, { role: 'assistant', content: `Could not generate the report: ${err.message || 'Network request failed.'}` }])
    } finally {
      setLoading(false)
    }
  }

  const suggestions = [
    { icon: 'chart', title: 'Summarize this data', prompt: 'Summarize this dataset and highlight the key takeaways.' },
    { icon: 'rows', title: 'Find patterns', prompt: 'What interesting patterns or trends can you find in this data?' },
    { icon: 'spark', title: 'Ask a question', prompt: 'Which columns have the most useful insights?' },
  ]

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-top">
          <a className="brand" href="#home" aria-label="Cloud Analyst home">
            <span className="brand-mark"><Icon name="spark" size={20} /></span>
            <span>control<span className="brand-light"> analyst</span></span>
          </a>
          <button className="icon-button new-chat" onClick={() => { setChatHistory([]); setSidebarOpen(false) }} aria-label="New chat"><Icon name="plus" size={18} /></button>
          <button className="icon-button mobile-close" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar"><Icon name="close" size={19} /></button>
        </div>

        <button className="new-chat-button" onClick={() => { setChatHistory([]); setSidebarOpen(false) }}><Icon name="plus" size={17} /> New analysis</button>

        <div className="sidebar-label">WORKSPACE</div>
        <div className="workspace-item"><span className="workspace-icon"><Icon name="chart" size={17} /></span><span>Data analyst</span><Icon name="chevron" size={15} /></div>

        <div className="sidebar-label dataset-label">YOUR DATA</div>
        <label className={`upload-card ${uploading ? 'is-uploading' : ''}`} htmlFor="dataset-upload">
          <span className="upload-card-icon"><Icon name="upload" size={18} /></span>
          <span className="upload-card-copy"><strong>{uploading ? 'Uploading…' : 'Upload a dataset'}</strong><small>CSV or Excel file</small></span>
          <input id="dataset-upload" type="file" accept=".csv,.xlsx,.xls" onChange={(e) => { setFile(e.target.files?.[0] || null); setError('') }} />
        </label>
        <button className="upload-action" onClick={handleUpload} disabled={uploading || !file}>{uploading ? 'Analyzing file…' : file ? 'Analyze dataset' : 'Choose a file above'}</button>

        {summary && (
          <div className="dataset-card">
            <div className="dataset-card-title"><span className="file-icon"><Icon name="file" size={16} /></span><span title={summary.filename}>{summary.filename}</span><span className="status-dot" /></div>
            <div className="dataset-stats"><span><b>{summary.rows.toLocaleString()}</b> rows</span><span><b>{summary.columns}</b> columns</span></div>
            <div className="column-list">{(summary.columns_names || []).slice(0, 5).map((column) => <span className="column-chip" key={column}>{column}</span>)}{summary.columns_names?.length > 5 && <span className="column-chip">+{summary.columns_names.length - 5}</span>}</div>
            <button className="sidebar-report" onClick={handleGenerateReport} disabled={loading}>{loading ? 'Generating report…' : 'Generate complete report'}</button>
            <button className="dataset-remove" onClick={handleDeleteDataset} disabled={uploading}>Delete dataset</button>
          </div>
        )}

        <div className="sidebar-footer"><div className="online-indicator" /><span>AI analyst ready</span><span className="footer-version">BETA</span></div>
      </aside>

      {sidebarOpen && <button className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close menu" />}

      <main className="main-panel">
        <header className="topbar">
          <button className="icon-button menu-button" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar"><Icon name="menu" size={20} /></button>
          <div className="breadcrumb"><span>Workspace</span><Icon name="chevron" size={14} /><strong>Data analyst</strong></div>
          <div className="topbar-right"><span className="secure-badge"><span /> Private workspace</span><div className="avatar">CA</div></div>
        </header>

        <section className={`conversation ${chatHistory.length ? 'has-messages' : ''}`}>
          {chatHistory.length === 0 ? (
            <div className="welcome-view">
              <div className="welcome-orb"><span className="orb-inner"><Icon name="spark" size={25} /></span></div>
              <div className="eyebrow"><span className="eyebrow-dot" /> YOUR AI DATA PARTNER</div>
              <h1>Make your data<br /><span>make sense.</span></h1>
              <p className="welcome-description">Ask questions in plain language. Get clear answers, discover patterns, and make confident decisions from your data.</p>
              {summary ? (
                <>
                  <div className="ready-banner"><span className="ready-check">✓</span><span><strong>{summary.filename}</strong> is ready. What would you like to know?</span></div>
                  <button className="report-button" onClick={handleGenerateReport} disabled={loading}>
                    <Icon name="spark" size={17} /> {loading ? 'Generating your report…' : 'Generate complete report'}
                  </button>
                </>
              ) : (
                <div className="upload-hint"><Icon name="upload" size={17} /><span>Start by uploading a CSV or Excel file in the sidebar</span></div>
              )}
              <div className="suggestion-grid">
                {suggestions.map((item) => <button className="suggestion-card" key={item.title} onClick={(e) => handleQuerySubmit(e, item.prompt)} disabled={!summary || loading}><span className="suggestion-icon"><Icon name={item.icon} size={18} /></span><span className="suggestion-title">{item.title}</span><span className="suggestion-prompt">{item.prompt}</span><span className="suggestion-arrow"><Icon name="chevron" size={16} /></span></button>)}
              </div>
            </div>
          ) : (
            <div className="message-list">
              {chatHistory.map((message, index) => <article className={`message-row ${message.role}`} key={`${index}-${message.role}`}>
                <div className={`message-avatar ${message.role === 'assistant' ? 'ai-avatar' : 'user-avatar'}`}>{message.role === 'assistant' ? <Icon name="sparkSmall" size={17} /> : 'You'}</div>
                <div className="message-content"><div className="message-label">{message.role === 'assistant' ? 'Cloud Analyst' : 'You'}</div>{message.role === 'assistant' ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown> : <p>{message.content}</p>}</div>
              </article>)}
              {loading && <article className="message-row assistant"><div className="message-avatar ai-avatar"><Icon name="sparkSmall" size={17} /></div><div className="message-content"><div className="message-label">Cloud Analyst</div><div className="thinking"><span /><span /><span /><em>Analyzing your data</em></div></div></article>}
              <div ref={chatEndRef} />
            </div>
          )}
        </section>

        <div className="composer-wrap">
          {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')} aria-label="Dismiss error"><Icon name="close" size={15} /></button></div>}
          <form className="composer" onSubmit={handleQuerySubmit}>
            <textarea value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleQuerySubmit(e) } }} placeholder={summary ? 'Ask anything about your data…' : 'Upload a dataset to start asking questions'} rows={1} aria-label="Ask about your data" />
            <div className="composer-bottom"><span className="composer-tip"><Icon name="sparkleSmall" size={14} /> AI can make mistakes. Verify important results.</span><button className="send-button" type="submit" disabled={loading || !query.trim() || !summary} aria-label="Send message"><Icon name="send" size={17} /></button></div>
          </form>
          <div className="composer-caption">Cloud Analyst <span>·</span> Your data stays private and secure</div>
        </div>
      </main>
    </div>
  )
}

export default App
