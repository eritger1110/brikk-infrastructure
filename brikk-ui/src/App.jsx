import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Activity, Users, MessageSquare, FileText, Settings, Shield } from 'lucide-react'
import './App.css'

// API helper functions
const API_BASE = '/api/v1'

const apiHelper = {
  async get(endpoint) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response.json()
  },

  async post(endpoint, data) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response.json()
  }
}

// Navigation component
function Navigation() {
  const location = useLocation()
  
  const navItems = [
    { path: '/app/agents', icon: Users, label: 'Agents' },
    { path: '/app/echo', icon: MessageSquare, label: 'Echo Test' },
    { path: '/app/logs', icon: FileText, label: 'Logs' },
  ]

  return (
    <nav className="bg-gray-900 border-b border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="flex items-center">
                <Shield className="h-8 w-8 text-blue-400" />
                <span className="ml-2 text-xl font-bold text-white">Brikk</span>
              </div>
            </div>
            <div className="hidden md:block">
              <div className="ml-10 flex items-baseline space-x-4">
                {navItems.map((item) => {
                  const Icon = item.icon
                  const isActive = location.pathname === item.path
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`px-3 py-2 rounded-md text-sm font-medium flex items-center ${
                        isActive
                          ? 'bg-gray-700 text-white'
                          : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                      }`}
                    >
                      <Icon className="h-4 w-4 mr-2" />
                      {item.label}
                    </Link>
                  )
                })}
              </div>
            </div>
          </div>
          <div className="flex items-center">
            <button className="bg-gray-800 p-1 rounded-full text-gray-400 hover:text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800 focus:ring-white">
              <Settings className="h-6 w-6" />
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}

// Agents page component
function AgentsPage() {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newAgent, setNewAgent] = useState({ name: '', description: '' })
  const [createdApiKey, setCreatedApiKey] = useState(null)

  useEffect(() => {
    loadAgents()
  }, [])

  const loadAgents = async () => {
    try {
      setLoading(true)
      const data = await apiHelper.get('/agents')
      setAgents(data.agents || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const createAgent = async (e) => {
    e.preventDefault()
    try {
      const data = await apiHelper.post('/agents', newAgent)
      setCreatedApiKey(data.api_key)
      setNewAgent({ name: '', description: '' })
      setShowCreateForm(false)
      loadAgents()
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-400"></div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-white">Agents</h1>
          <button
            onClick={() => setShowCreateForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md"
          >
            Create Agent
          </button>
        </div>

        {error && (
          <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded mb-4">
            Error: {error}
          </div>
        )}

        {createdApiKey && (
          <div className="bg-green-900 border border-green-700 text-green-100 px-4 py-3 rounded mb-4">
            <p className="font-semibold">Agent created successfully!</p>
            <p className="text-sm mt-1">API Key (save this, it won't be shown again):</p>
            <code className="block bg-green-800 p-2 rounded mt-2 text-xs break-all">
              {createdApiKey}
            </code>
            <button
              onClick={() => setCreatedApiKey(null)}
              className="mt-2 text-sm underline hover:no-underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {showCreateForm && (
          <div className="bg-gray-800 p-6 rounded-lg mb-6">
            <h2 className="text-xl font-semibold text-white mb-4">Create New Agent</h2>
            <form onSubmit={createAgent}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Agent Name
                </label>
                <input
                  type="text"
                  value={newAgent.name}
                  onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={newAgent.description}
                  onChange={(e) => setNewAgent({ ...newAgent, description: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows="3"
                />
              </div>
              <div className="flex space-x-3">
                <button
                  type="submit"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md"
                >
                  Create Agent
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <div key={agent.id} className="bg-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  agent.status === 'active' 
                    ? 'bg-green-900 text-green-100' 
                    : 'bg-gray-700 text-gray-300'
                }`}>
                  {agent.status}
                </span>
              </div>
              {agent.description && (
                <p className="text-gray-300 text-sm mb-4">{agent.description}</p>
              )}
              <div className="text-xs text-gray-400">
                <p>ID: {agent.id}</p>
                <p>Created: {new Date(agent.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          ))}
        </div>

        {agents.length === 0 && !loading && (
          <div className="text-center py-12">
            <Users className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-300">No agents</h3>
            <p className="mt-1 text-sm text-gray-400">
              Get started by creating your first agent.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// Echo Test page component
function EchoTestPage() {
  const [message, setMessage] = useState('')
  const [senderId, setSenderId] = useState('')
  const [response, setResponse] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const sendEcho = async (e) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)
      const data = await apiHelper.post('/echo', {
        message,
        sender_id: senderId || undefined
      })
      setResponse(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <h1 className="text-3xl font-bold text-white mb-6">Echo Test</h1>
        
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">Send Echo Message</h2>
          <form onSubmit={sendEcho}>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Message
              </label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows="4"
                placeholder="Enter your message to echo..."
                required
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Sender ID (optional)
              </label>
              <input
                type="text"
                value={senderId}
                onChange={(e) => setSenderId(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Agent UUID (optional)"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white px-4 py-2 rounded-md"
            >
              {loading ? 'Sending...' : 'Send Echo'}
            </button>
          </form>
        </div>

        {error && (
          <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded mb-4">
            Error: {error}
          </div>
        )}

        {response && (
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Echo Response</h2>
            <div className="bg-gray-900 p-4 rounded-md">
              <pre className="text-green-400 text-sm overflow-x-auto">
                {JSON.stringify(response, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Logs page component
function LogsPage() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadLogs()
  }, [])

  const loadLogs = async () => {
    try {
      setLoading(true)
      const data = await apiHelper.get('/echo/logs')
      setLogs(data.logs || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-400"></div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-white">Message Logs</h1>
          <button
            onClick={loadLogs}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md"
          >
            Refresh
          </button>
        </div>

        {error && (
          <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded mb-4">
            Error: {error}
          </div>
        )}

        <div className="space-y-4">
          {logs.map((log) => (
            <div key={log.id} className="bg-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-4">
                  <span className="text-sm font-medium text-gray-300">
                    ID: {log.id}
                  </span>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    log.status === 'success' 
                      ? 'bg-green-900 text-green-100' 
                      : 'bg-red-900 text-red-100'
                  }`}>
                    {log.status}
                  </span>
                </div>
                <span className="text-sm text-gray-400">
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
              
              {log.sender_id && (
                <div className="mb-2">
                  <span className="text-sm text-gray-400">Sender: </span>
                  <span className="text-sm text-gray-300">{log.sender_id}</span>
                </div>
              )}

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-300 mb-2">Request</h4>
                  <div className="bg-gray-900 p-3 rounded text-xs">
                    <pre className="text-gray-400 overflow-x-auto">
                      {JSON.stringify(log.request_payload, null, 2)}
                    </pre>
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-300 mb-2">Response</h4>
                  <div className="bg-gray-900 p-3 rounded text-xs">
                    <pre className="text-gray-400 overflow-x-auto">
                      {JSON.stringify(log.response_payload, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {logs.length === 0 && !loading && (
          <div className="text-center py-12">
            <FileText className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-300">No logs</h3>
            <p className="mt-1 text-sm text-gray-400">
              Message logs will appear here after you send echo messages.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// Main App component
function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-900">
        <Navigation />
        <main>
          <Routes>
            <Route path="/app/agents" element={<AgentsPage />} />
            <Route path="/app/echo" element={<EchoTestPage />} />
            <Route path="/app/logs" element={<LogsPage />} />
            <Route path="/" element={
              <div className="max-w-4xl mx-auto py-12 px-4 text-center">
                <Shield className="mx-auto h-16 w-16 text-blue-400 mb-4" />
                <h1 className="text-4xl font-bold text-white mb-4">
                  Brikk Agent Platform
                </h1>
                <p className="text-xl text-gray-300 mb-8">
                  Stage 1: Agent Core + Echo Workflow
                </p>
                <div className="grid md:grid-cols-3 gap-6 max-w-2xl mx-auto">
                  <Link to="/app/agents" className="bg-gray-800 hover:bg-gray-700 p-6 rounded-lg transition-colors">
                    <Users className="h-8 w-8 text-blue-400 mx-auto mb-2" />
                    <h3 className="text-lg font-semibold text-white">Agents</h3>
                    <p className="text-sm text-gray-400">Manage your agents</p>
                  </Link>
                  <Link to="/app/echo" className="bg-gray-800 hover:bg-gray-700 p-6 rounded-lg transition-colors">
                    <MessageSquare className="h-8 w-8 text-blue-400 mx-auto mb-2" />
                    <h3 className="text-lg font-semibold text-white">Echo Test</h3>
                    <p className="text-sm text-gray-400">Test messaging</p>
                  </Link>
                  <Link to="/app/logs" className="bg-gray-800 hover:bg-gray-700 p-6 rounded-lg transition-colors">
                    <FileText className="h-8 w-8 text-blue-400 mx-auto mb-2" />
                    <h3 className="text-lg font-semibold text-white">Logs</h3>
                    <p className="text-sm text-gray-400">View message history</p>
                  </Link>
                </div>
              </div>
            } />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
