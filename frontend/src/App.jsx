
import { useEffect, useState } from 'react'
import './App.css'

const API = 'http://127.0.0.1:8000'

function App() {
  const [dashboard, setDashboard] = useState(null)
  const [customerId, setCustomerId] = useState('CUS-000001')
  const [customer, setCustomer] = useState(null)
  const [question, setQuestion] = useState('')
  const [chat, setChat] = useState([])
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function loadDashboard() {
    try {
      setError('')

      const dashResponse = await fetch(`${API}/api/kyc/dashboard`)
      if (!dashResponse.ok) {
        throw new Error('Unable to load dashboard metrics')
      }

      const dashboardData = await dashResponse.json()
      setDashboard({
        total_customers: Number(dashboardData.total_customers ?? 0),
        compliant_customers: Number(dashboardData.compliant_customers ?? 0),
        non_compliant_customers: Number(dashboardData.non_compliant_customers ?? 0),
        high_risk_customers: Number(dashboardData.high_risk_customers ?? 0),
        active_alerts: Number(dashboardData.active_alerts ?? 0),
        overdue_reviews: Number(dashboardData.overdue_reviews ?? 0),
        total_anomalies: Number(dashboardData.total_anomalies ?? 0)
      })

      const anomalyResponse = await fetch(`${API}/api/kyc/anomalies`)
      if (!anomalyResponse.ok) {
        throw new Error('Unable to load anomalies')
      }

      const anomalyData = await anomalyResponse.json()

      setAnomalies(
        Array.isArray(anomalyData.anomalies)
          ? anomalyData.anomalies
          : Array.isArray(anomalyData)
            ? anomalyData
            : []
      )
    } catch (err) {
      console.error(err)
      setError(err.message)
    }
  }

  async function analyzeCustomer() {
    setLoading(true)
    setError('')

    try {
      const response = await fetch(
        `${API}/api/ai/explain/${encodeURIComponent(customerId)}`
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Customer lookup failed')
      }

      setCustomer(data)
    } catch (err) {
      setError(err.message)
      setCustomer(null)
    } finally {
      setLoading(false)
    }
  }

  async function sendQuestion(e) {
    e.preventDefault()

    if (!question.trim()) return

    const currentQuestion = question.trim()

    setChat(prev => [
      ...prev,
      { role: 'user', text: currentQuestion }
    ])

    setQuestion('')
    setLoading(true)

    try {
      const response = await fetch(`${API}/api/ai/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          customer_id: customerId,
          question: currentQuestion
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Copilot request failed')
      }

      setChat(prev => [
        ...prev,
        { role: 'assistant', text: data.answer }
      ])
    } catch (err) {
      setChat(prev => [
        ...prev,
        { role: 'assistant', text: `Error: ${err.message}` }
      ])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()
    analyzeCustomer()
  }, [])

  const metrics = [
    ['Total Customers', dashboard ? dashboard.total_customers.toLocaleString('en-IN') : 'Loading...', '♙'],
    ['Compliant', dashboard ? dashboard.compliant_customers.toLocaleString('en-IN') : 'Loading...', '✓'],
    ['Non-Compliant', dashboard ? dashboard.non_compliant_customers.toLocaleString('en-IN') : 'Loading...', '!'],
    ['High Risk', dashboard ? dashboard.high_risk_customers.toLocaleString('en-IN') : 'Loading...', '⚑'],
    ['Active Alerts', dashboard ? dashboard.active_alerts.toLocaleString('en-IN') : 'Loading...', '♢'],
    ['Overdue Reviews', dashboard ? dashboard.overdue_reviews.toLocaleString('en-IN') : 'Loading...', '◷']
  ]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">K</div>
          <div>
            <strong>KYC INTELLIGENCE</strong>
            <span>COMPLIANCE PLATFORM</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <a className="nav-item active" href="#overview">▦ <span>Overview</span></a>
        <a className="nav-item" href="#customer">♙ <span>Customer Review</span></a>
        <a className="nav-item" href="#alerts">♢ <span>Risk & Anomalies</span></a>
        <a className="nav-item" href="#copilot">✧ <span>AI Copilot</span></a>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot"></span> System operational
          </div>
          <div className="profile">
            <div className="avatar">A</div>
            <div>
              <strong>Compliance Analyst</strong>
              <span>Administrator</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="breadcrumb">Workspace /</span> Overview
          </div>
          <div className="top-actions">
            <span className="live-indicator">● LIVE SYSTEM</span>
            <button onClick={loadDashboard}>↻ Refresh</button>
          </div>
        </header>

        <section id="overview" className="page-heading">
          <div>
            <p className="eyebrow">COMPLIANCE OPERATIONS</p>
            <h1>KYC Intelligence Dashboard</h1>
            <p className="subheading">
              Monitor customer verification, risk exposure and compliance exceptions.
            </p>
          </div>
          <div className="date-chip">◷ &nbsp; Live metrics</div>
        </section>

        {error && <div className="error-banner">{error}</div>}

        <section className="metrics-grid">
          {metrics.map(([label, value, icon]) => (
            <div className="metric-card" key={label}>
              <div className="metric-top">
                <span>{label}</span>
                <span className="metric-icon">{icon}</span>
              </div>
              <strong>{value}</strong>
              <small>Current system count</small>
            </div>
          ))}
        </section>

        <div className="content-grid">
          <section id="customer" className="panel customer-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">CUSTOMER INTELLIGENCE</p>
                <h2>Customer compliance review</h2>
              </div>
              <span className="panel-symbol">♙</span>
            </div>

            <form
              className="search-form"
              onSubmit={e => {
                e.preventDefault()
                analyzeCustomer()
              }}
            >
              <input
                value={customerId}
                onChange={e => setCustomerId(e.target.value)}
                placeholder="Enter customer ID"
              />
              <button disabled={loading}>
                {loading ? 'Loading...' : 'Analyze'}
              </button>
            </form>

            {customer && (
              <div className="customer-result">
                <div className="customer-identity">
                  <div className="customer-avatar">
                    {customer.customer_name?.charAt(0) || 'C'}
                  </div>
                  <div>
                    <h3>{customer.customer_name || customer.customer_id}</h3>
                    <span>{customer.customer_type} · {customer.customer_id}</span>
                  </div>
                  <span className={`status-pill ${customer.compliance_status === 'COMPLIANT' ? 'good' : 'bad'}`}>
                    {customer.compliance_status}
                  </span>
                </div>

                <div className="customer-stats">
                  <div><small>Risk level</small><strong>{customer.risk_level}</strong></div>
                  <div><small>Risk score</small><strong>{customer.risk_score ?? '—'}</strong></div>
                  <div><small>Active alerts</small><strong>{customer.active_alert_count ?? 0}</strong></div>
                  <div><small>Audit events</small><strong>{customer.audit_event_count ?? 0}</strong></div>
                </div>

                <h4>Compliance issues</h4>
                {customer.compliance_issues?.length ? (
                  customer.compliance_issues.map((issue, i) => (
                    <div className="issue-row" key={i}>
                      <span>!</span>{issue}
                    </div>
                  ))
                ) : (
                  <p className="muted">No compliance issues detected.</p>
                )}

                <h4>Recommended actions</h4>
                {customer.recommendations?.map((item, i) => (
                  <div className="recommendation" key={i}>
                    <span>✓</span>{item}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section id="copilot" className="panel copilot-panel">
            <div className="copilot-heading">
              <div className="sparkle">✧</div>
              <div>
                <p className="eyebrow">INTELLIGENT ASSISTANT</p>
                <h2>AI Compliance Copilot</h2>
                <span>Rule-grounded compliance assistant</span>
              </div>
              <span className="online-tag">ONLINE</span>
            </div>

            <div className="chat-messages">
              <div className="assistant-message">
                <div className="bot-avatar">✧</div>
                <div>
                  <strong>Compliance Copilot</strong>
                  <p>
                    Hello! I can explain customer compliance, missing documents,
                    risk ratings, alerts and audit history.
                  </p>
                </div>
              </div>

              {chat.map((message, i) => (
                <div className={`chat-message ${message.role}`} key={i}>
                  {message.role === 'assistant' && <div className="bot-avatar">✧</div>}
                  <div className="message-bubble">{message.text}</div>
                </div>
              ))}

              {loading && <div className="typing">Copilot is analyzing...</div>}
            </div>

            <div className="quick-questions">
              {[
                'Why is this customer non-compliant?',
                'Which documents are missing?',
                'Explain customer risk',
                'Show audit history'
              ].map(q => (
                <button key={q} onClick={() => setQuestion(q)}>{q}</button>
              ))}
            </div>

            <form className="chat-form" onSubmit={sendQuestion}>
              <input
                value={question}
                onChange={e => setQuestion(e.target.value)}
                placeholder="Ask about this customer..."
              />
              <button disabled={loading || !question.trim()}>➤</button>
            </form>

            <p className="copilot-note">
              AI explanations are grounded in deterministic Python compliance rules.
            </p>
          </section>
        </div>

        <section id="alerts" className="panel anomalies-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">EXCEPTION MANAGEMENT</p>
              <h2>Detected anomalies</h2>
            </div>
            <span className="anomaly-count">
              {dashboard?.total_anomalies ?? anomalies.length} detected
            </span>
          </div>

          {anomalies.length ? (
            <div className="anomaly-list">
              {anomalies.map((item, i) => (
                <div className="anomaly-row" key={i}>
                  <span className="anomaly-mark">!</span>
                  <div>
                    <strong>{(item.anomaly_type || 'ANOMALY').replaceAll('_', ' ')}</strong>
                    <p>{item.evidence || item.description || item.entity_id}</p>
                  </div>
                  <span className="exception-label">EXCEPTION</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">Loading anomalies or no anomaly records found.</p>
          )}
        </section>

        <footer>
          KYC Intelligence Platform <span>·</span> Compliance decisions powered by deterministic rules
        </footer>
      </main>
    </div>
  )
}

export default App
