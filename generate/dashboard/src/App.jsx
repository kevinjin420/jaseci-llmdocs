import { useState, useEffect, useRef } from 'react'

function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`
}

function StageCard({ stage, isActive }) {
  const statusColors = {
    pending: 'bg-zinc-700',
    running: 'bg-blue-600 animate-pulse',
    complete: 'bg-green-600',
    error: 'bg-red-600',
  }

  return (
    <div className={`p-4 rounded-lg border ${isActive ? 'border-blue-500 bg-zinc-800' : 'border-zinc-700 bg-zinc-900'}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-white">{stage.name}</h3>
        <span className={`px-2 py-1 rounded text-xs text-white ${statusColors[stage.status]}`}>
          {stage.status}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="text-zinc-400">Input:</div>
        <div className="text-white">{formatBytes(stage.input_size)}</div>

        <div className="text-zinc-400">Output:</div>
        <div className="text-white">{formatBytes(stage.output_size)}</div>

        <div className="text-zinc-400">Ratio:</div>
        <div className={`${stage.compression_ratio < 0.5 ? 'text-green-400' : 'text-white'}`}>
          {stage.input_size > 0 ? `${(stage.compression_ratio * 100).toFixed(0)}%` : '-'}
        </div>

        <div className="text-zinc-400">Duration:</div>
        <div className="text-white">{formatDuration(stage.duration)}</div>

        <div className="text-zinc-400">Files:</div>
        <div className="text-white">{stage.file_count || stage.files?.length || 0}</div>
      </div>

      {stage.files?.length > 0 && stage.status === 'complete' && (
        <details className="mt-3">
          <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-300">
            View files ({stage.files.length})
          </summary>
          <div className="mt-2 max-h-32 overflow-y-auto text-xs">
            {stage.files.slice(0, 10).map((f, i) => (
              <div key={i} className="flex justify-between text-zinc-400 py-0.5">
                <span className="truncate mr-2">{f.name}</span>
                <span>{formatBytes(f.size)}</span>
              </div>
            ))}
            {stage.files.length > 10 && (
              <div className="text-zinc-500">...and {stage.files.length - 10} more</div>
            )}
          </div>
        </details>
      )}

      {stage.error && (
        <div className="mt-2 p-2 bg-red-900/50 rounded text-xs text-red-300">
          {stage.error}
        </div>
      )}
    </div>
  )
}

function ValidationCard({ validation }) {
  if (!validation) return null

  return (
    <div className={`p-4 rounded-lg border ${validation.is_valid ? 'border-green-600 bg-green-900/20' : 'border-yellow-600 bg-yellow-900/20'}`}>
      <h3 className="font-medium text-white mb-3">Validation</h3>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="text-zinc-400">Status:</div>
        <div className={validation.is_valid ? 'text-green-400' : 'text-yellow-400'}>
          {validation.is_valid ? 'PASSED' : 'WARNINGS'}
        </div>
        <div className="text-zinc-400">Patterns:</div>
        <div className="text-white">{validation.patterns_found}/{validation.patterns_total}</div>
      </div>
      {validation.missing_patterns?.length > 0 && (
        <div className="mt-2 text-xs text-yellow-400">
          Missing: {validation.missing_patterns.join(', ')}
        </div>
      )}
      {validation.issues?.length > 0 && (
        <div className="mt-2 text-xs text-yellow-400">
          {validation.issues.join(', ')}
        </div>
      )}
    </div>
  )
}

function LogEntry({ event }) {
  const colors = {
    pipeline_start: 'text-blue-400',
    pipeline_complete: 'text-green-400',
    pipeline_error: 'text-red-400',
    stage_start: 'text-cyan-400',
    stage_complete: 'text-green-400',
    stage_error: 'text-red-400',
  }

  return (
    <div className="text-xs font-mono py-1 border-b border-zinc-800">
      <span className="text-zinc-500">{new Date(event.timestamp).toLocaleTimeString()}</span>
      <span className={`ml-2 ${colors[event.event] || 'text-white'}`}>{event.event}</span>
      {event.data?.stage && <span className="ml-2 text-zinc-400">[{event.data.stage}]</span>}
    </div>
  )
}

function App() {
  const [connected, setConnected] = useState(false)
  const [running, setRunning] = useState(false)
  const [stages, setStages] = useState({
    extract: { name: 'Topic Extraction', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1 },
    merge: { name: 'Topic Merging', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1 },
    reduce: { name: 'Hierarchical Reduction', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1 },
    compress: { name: 'Final Minification', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1 },
  })
  const [validation, setValidation] = useState(null)
  const [logs, setLogs] = useState([])
  const [metrics, setMetrics] = useState(null)
  const wsRef = useRef(null)
  const logsEndRef = useRef(null)

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`ws://${window.location.hostname}:4000/ws`)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        setTimeout(connect, 2000)
      }

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        setLogs(prev => [...prev.slice(-99), msg])

        if (msg.event === 'pipeline_start') {
          setRunning(true)
          setValidation(null)
        }

        if (msg.event === 'pipeline_complete' || msg.event === 'pipeline_error') {
          setRunning(false)
          if (msg.data) setMetrics(msg.data)
        }

        if (msg.event === 'stage_start') {
          setStages(prev => ({
            ...prev,
            [msg.data.stage]: { ...prev[msg.data.stage], status: 'running' }
          }))
        }

        if (msg.event === 'stage_complete' && msg.data?.metrics) {
          setStages(prev => ({
            ...prev,
            [msg.data.stage]: { ...prev[msg.data.stage], ...msg.data.metrics, status: 'complete' }
          }))
          if (msg.data.validation) {
            setValidation(msg.data.validation)
          }
        }

        if (msg.event === 'stage_error') {
          setStages(prev => ({
            ...prev,
            [msg.data.stage]: { ...prev[msg.data.stage], status: 'error', error: msg.data.error }
          }))
        }
      }
    }

    connect()
    return () => wsRef.current?.close()
  }, [])

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const runPipeline = async () => {
    setLogs([])
    setStages({
      extract: { name: 'Topic Extraction', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1 },
      merge: { name: 'Topic Merging', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1 },
      reduce: { name: 'Hierarchical Reduction', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1 },
      compress: { name: 'Final Minification', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1 },
    })
    setValidation(null)
    setMetrics(null)

    try {
      await fetch('/api/run', { method: 'POST' })
    } catch (err) {
      console.error(err)
    }
  }

  const activeStage = Object.keys(stages).find(k => stages[k].status === 'running')
  const totalInput = stages.extract.input_size
  const totalOutput = stages.compress.output_size
  const overallRatio = totalInput > 0 ? totalOutput / totalInput : 0

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Pipeline Dashboard</h1>
            <p className="text-zinc-500 text-sm">Documentation compression pipeline</p>
          </div>
          <div className="flex items-center gap-4">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-zinc-400">{connected ? 'Connected' : 'Disconnected'}</span>
            <button
              onClick={runPipeline}
              disabled={running || !connected}
              className={`px-4 py-2 rounded font-medium transition ${
                running || !connected
                  ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-500 text-white'
              }`}
            >
              {running ? 'Running...' : 'Run Pipeline'}
            </button>
          </div>
        </div>

        {(totalInput > 0 || metrics) && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
              <div className="text-zinc-500 text-sm">Total Input</div>
              <div className="text-xl font-bold">{formatBytes(totalInput)}</div>
            </div>
            <div className="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
              <div className="text-zinc-500 text-sm">Total Output</div>
              <div className="text-xl font-bold">{formatBytes(totalOutput)}</div>
            </div>
            <div className="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
              <div className="text-zinc-500 text-sm">Compression</div>
              <div className={`text-xl font-bold ${overallRatio < 0.05 ? 'text-green-400' : ''}`}>
                {overallRatio > 0 ? `${(overallRatio * 100).toFixed(2)}%` : '-'}
              </div>
            </div>
            <div className="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
              <div className="text-zinc-500 text-sm">Duration</div>
              <div className="text-xl font-bold">
                {metrics?.total_duration ? formatDuration(metrics.total_duration) : '-'}
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {Object.entries(stages).map(([key, stage]) => (
            <StageCard key={key} stage={stage} isActive={activeStage === key} />
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ValidationCard validation={validation} />

          <div className="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
            <h3 className="font-medium text-white mb-3">Event Log</h3>
            <div className="h-48 overflow-y-auto bg-zinc-950 rounded p-2">
              {logs.length === 0 ? (
                <div className="text-zinc-600 text-sm">No events yet</div>
              ) : (
                logs.map((log, i) => <LogEntry key={i} event={log} />)
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
