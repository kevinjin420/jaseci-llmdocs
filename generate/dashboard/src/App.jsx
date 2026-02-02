import { useState, useEffect, useRef } from 'react'
import PipelinePage from './pages/PipelinePage'
import ConfigPage from './pages/ConfigPage'

const INITIAL_STAGES = {
  fetch: { name: 'Fetch & Sanitize', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
  extract: { name: 'Deterministic Extract', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
  assemble: { name: 'LLM Assembly', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
  validate: { name: 'Validation', status: 'pending' },
}

export default function App() {
  const [page, setPage] = useState('pipeline')
  const [connected, setConnected] = useState(false)
  const [running, setRunning] = useState(false)
  const [sources, setSources] = useState([])
  const [stages, setStages] = useState(INITIAL_STAGES)
  const [progress, setProgress] = useState({})
  const [validation, setValidation] = useState(null)
  const [logs, setLogs] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [streamingText, setStreamingText] = useState('')
  const [candidateContent, setCandidateContent] = useState('')
  const wsRef = useRef(null)

  const fetchCandidate = async () => {
    try {
      const res = await fetch('/api/candidate')
      if (res.ok) {
        const data = await res.json()
        setCandidateContent(data.content)
      }
    } catch (err) {
      console.error('Failed to fetch candidate:', err)
    }
  }

  const fetchSources = async () => {
    try {
      const res = await fetch('/api/sources')
      const data = await res.json()
      setSources(data)
    } catch (err) {
      console.error('Failed to fetch sources:', err)
    }
  }

  const addSource = async (sourceData) => {
    const res = await fetch('/api/sources', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sourceData),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to add source')
    }
    await fetchSources()
  }

  const deleteSource = async (id) => {
    if (!confirm(`Delete source "${id}"?`)) return
    try {
      await fetch(`/api/sources/${id}`, { method: 'DELETE' })
      await fetchSources()
    } catch (err) {
      console.error('Failed to delete source:', err)
    }
  }

  const toggleSource = async (id) => {
    try {
      await fetch(`/api/sources/${id}/toggle`, { method: 'POST' })
      await fetchSources()
    } catch (err) {
      console.error('Failed to toggle source:', err)
    }
  }

  const editSource = async (id, updates) => {
    const res = await fetch(`/api/sources/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to update source')
    }
    await fetchSources()
  }

  useEffect(() => {
    let mounted = true

    const init = async () => {
      try {
        const [sourcesRes, statusRes, stagesRes] = await Promise.all([
          fetch('/api/sources'),
          fetch('/api/status'),
          fetch('/api/stages')
        ])

        if (!mounted) return

        const sourcesData = await sourcesRes.json()
        const statusData = await statusRes.json()
        const stagesData = await stagesRes.json()

        setSources(sourcesData)
        setRunning(statusData.is_running)

        if (stagesData.length > 0) {
          const stageKeys = ['fetch', 'extract', 'assemble']
          setStages(prev => {
            const newStages = { ...prev }
            stagesData.forEach((s, i) => {
              const key = stageKeys[i]
              if (key) newStages[key] = { ...prev[key], ...s }
            })
            return newStages
          })
        }

        if (statusData.is_running) {
          const metricsRes = await fetch('/api/metrics')
          if (!mounted) return
          const metricsData = await metricsRes.json()
          if (metricsData.validation) setValidation(metricsData.validation)
        }

        // Load existing candidate if available
        try {
          const candidateRes = await fetch('/api/candidate')
          if (candidateRes.ok) {
            const candidateData = await candidateRes.json()
            setCandidateContent(candidateData.content)
          }
        } catch {}
      } catch (err) {
        console.error('Failed to initialize:', err)
      }
    }

    init()
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    let cancelled = false

    const connect = () => {
      if (cancelled) return
      const ws = new WebSocket(`ws://${window.location.hostname}:4000/ws`)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!cancelled) setTimeout(connect, 2000)
      }

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)

        if (msg.event !== 'progress' && msg.event !== 'llm_token') {
          setLogs(prev => [...prev.slice(-99), msg])
        }

        if (msg.event === 'llm_token') {
          setStreamingText(prev => prev + msg.data.token)
        }

        if (msg.event === 'pipeline_start') {
          setRunning(true)
          setValidation(null)
          setProgress({})
          setStreamingText('')
        }

        if (msg.event === 'pipeline_complete') {
          setRunning(false)
          setProgress({})
          if (msg.data) setMetrics(msg.data)
          fetchCandidate()
        }

        if (msg.event === 'pipeline_error') {
          setRunning(false)
          setProgress({})
          if (msg.data) setMetrics(msg.data)
        }

        if (msg.event === 'progress') {
          setProgress(prev => ({
            ...prev,
            [msg.data.stage]: {
              current: msg.data.current,
              total: msg.data.total,
              message: msg.data.message
            }
          }))
        }

        if (msg.event === 'stage_start') {
          setStages(prev => ({
            ...prev,
            [msg.data.stage]: { ...prev[msg.data.stage], status: 'running' }
          }))
          if (msg.data.stage === 'assemble') setStreamingText('')
        }

        if (msg.event === 'stage_complete' && msg.data?.metrics) {
          setStages(prev => ({
            ...prev,
            [msg.data.stage]: { ...prev[msg.data.stage], ...msg.data.metrics, status: 'complete' }
          }))
          setProgress(prev => {
            const next = { ...prev }
            delete next[msg.data.stage]
            return next
          })
          if (msg.data.validation) setValidation(msg.data.validation)
        }

        if (msg.event === 'stage_error') {
          setStages(prev => ({
            ...prev,
            [msg.data.stage]: { ...prev[msg.data.stage], status: 'error', error: msg.data.error }
          }))
        }

        if (msg.event === 'validation') {
          setValidation(prev => ({ ...prev, ...msg.data, _lastUpdate: Date.now() }))
        }

        if (msg.event === 'warning') {
          setLogs(prev => [...prev.slice(-99), msg])
        }
      }
    }

    connect()
    return () => {
      cancelled = true
      wsRef.current?.close()
    }
  }, [])

  const runPipeline = async () => {
    setRunning(true)
    setLogs([])
    setStages(INITIAL_STAGES)
    setValidation(null)
    setMetrics(null)
    setProgress({})
    setStreamingText('')

    try {
      await fetch('/api/run', { method: 'POST' })
    } catch (err) {
      console.error(err)
      setRunning(false)
    }
  }

  const runStage = async (stageKey) => {
    setRunning(true)
    setStages(prev => ({
      ...prev,
      [stageKey]: { ...prev[stageKey], status: 'running', error: null }
    }))

    try {
      await fetch(`/api/run/${stageKey}`, { method: 'POST' })
    } catch (err) {
      console.error(err)
      setRunning(false)
      setStages(prev => ({
        ...prev,
        [stageKey]: { ...prev[stageKey], status: 'error', error: 'Failed to start stage' }
      }))
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-6 font-jetbrains">
      <div className="max-w-6xl mx-auto">
        <Header
          page={page}
          setPage={setPage}
          connected={connected}
          running={running}
          onRunPipeline={runPipeline}
        />

        {page === 'config' && (
          <ConfigPage
            sources={sources}
            onAdd={addSource}
            onDelete={deleteSource}
            onToggle={toggleSource}
            onRefresh={fetchSources}
            onEdit={editSource}
          />
        )}

        {page === 'pipeline' && (
          <PipelinePage
            stages={stages}
            progress={progress}
            validation={validation}
            logs={logs}
            metrics={metrics}
            streamingText={streamingText}
            candidateContent={candidateContent}
            running={running}
            connected={connected}
            onRunStage={runStage}
          />
        )}
      </div>
    </div>
  )
}

function Header({ page, setPage, connected, running, onRunPipeline }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex items-center gap-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Pipeline Dashboard</h1>
          <p className="text-zinc-500 text-xs">Documentation compression pipeline</p>
        </div>
        <div className="flex gap-1 bg-zinc-900/80 rounded-lg p-1 border border-zinc-800">
          <button
            onClick={() => setPage('pipeline')}
            className={`px-4 py-1.5 text-xs rounded-md transition ${
              page === 'pipeline' ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Pipeline
          </button>
          <button
            onClick={() => setPage('config')}
            className={`px-4 py-1.5 text-xs rounded-md transition ${
              page === 'config' ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Config
          </button>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-emerald-400' : 'bg-red-400'}`} />
          <span className="text-xs text-zinc-500">{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
        {page === 'pipeline' && (
          <button
            onClick={onRunPipeline}
            disabled={running || !connected}
            className={`px-4 py-2 rounded text-xs font-medium transition border ${
              running || !connected
                ? 'bg-zinc-800/50 border-zinc-700/50 text-zinc-500 cursor-not-allowed'
                : 'bg-emerald-800/60 border-emerald-700/50 text-emerald-100 hover:bg-emerald-700/60'
            }`}
          >
            {running ? 'Running...' : 'Run Pipeline'}
          </button>
        )}
      </div>
    </div>
  )
}
