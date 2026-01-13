import { useState, useEffect, useRef } from 'react'
import Editor from '@monaco-editor/react'

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

function ProgressBar({ current, total, message }) {
  const percent = total > 0 ? (current / total) * 100 : 0

  return (
    <div className="mt-3">
      <div className="flex justify-between text-xs text-zinc-400 mb-1">
        <span className="truncate max-w-[70%]">{message || 'Processing...'}</span>
        <span>{current}/{total}</span>
      </div>
      <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 transition-all duration-200"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}

function SourcePanel({ sources, onAdd, onDelete, onToggle, onRefresh }) {
  const [expanded, setExpanded] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    id: '',
    git_url: '',
    branch: 'main',
    path: '.',
    source_type: 'docs',
  })
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (!formData.id || !formData.git_url) {
      setError('ID and Git URL are required')
      return
    }

    try {
      await onAdd(formData)
      setFormData({
        id: '',
        git_url: '',
        branch: 'main',
        path: '.',
        source_type: 'docs',
      })
      setShowForm(false)
    } catch (err) {
      setError(err.message)
    }
  }

  const sourceTypeLabels = {
    docs: 'Documentation',
    jac: 'Jac Code',
    both: 'Both',
  }

  const enabledCount = sources.filter(s => s.enabled).length

  return (
    <div className="bg-zinc-900 rounded-lg border border-zinc-800 mb-6">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-zinc-800 rounded-lg transition"
      >
        <div className="flex items-center gap-3">
          <span className={`text-zinc-400 text-xs transition-transform ${expanded ? 'rotate-90' : ''}`}>&gt;</span>
          <h3 className="font-medium text-white">Sources</h3>
          <span className="text-xs text-zinc-500">({enabledCount} enabled)</span>
        </div>
        <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={onRefresh}
            className="px-3 py-1 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded transition"
          >
            Refresh
          </button>
          <button
            onClick={() => { setShowForm(!showForm); setExpanded(true) }}
            className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded transition"
          >
            {showForm ? 'Cancel' : 'Add'}
          </button>
        </div>
      </button>

      {expanded && <div className="px-4 pb-4">
      {showForm && (
        <form onSubmit={handleSubmit} className="mb-4 p-3 bg-zinc-800 rounded-lg">
          {error && (
            <div className="mb-3 p-2 bg-red-900/50 text-red-300 text-xs rounded">
              {error}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs text-zinc-400 mb-1">ID</label>
              <input
                type="text"
                value={formData.id}
                onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                placeholder="my-source"
                className="w-full px-2 py-1 text-sm bg-zinc-900 border border-zinc-700 rounded text-white"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-zinc-400 mb-1">Git URL</label>
              <input
                type="text"
                value={formData.git_url}
                onChange={(e) => setFormData({ ...formData, git_url: e.target.value })}
                placeholder="https://github.com/user/repo.git"
                className="w-full px-2 py-1 text-sm bg-zinc-900 border border-zinc-700 rounded text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Branch</label>
              <input
                type="text"
                value={formData.branch}
                onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                placeholder="main"
                className="w-full px-2 py-1 text-sm bg-zinc-900 border border-zinc-700 rounded text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Path</label>
              <input
                type="text"
                value={formData.path}
                onChange={(e) => setFormData({ ...formData, path: e.target.value })}
                placeholder="docs/"
                className="w-full px-2 py-1 text-sm bg-zinc-900 border border-zinc-700 rounded text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Type</label>
              <select
                value={formData.source_type}
                onChange={(e) => setFormData({ ...formData, source_type: e.target.value })}
                className="w-full px-2 py-1 text-sm bg-zinc-900 border border-zinc-700 rounded text-white"
              >
                <option value="docs">Documentation (.md)</option>
                <option value="jac">Jac Code (.jac)</option>
                <option value="both">Both</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                className="w-full px-3 py-1 text-sm bg-green-600 hover:bg-green-500 text-white rounded transition"
              >
                Add Source
              </button>
            </div>
          </div>
        </form>
      )}

      <div className="space-y-2">
        {sources.length === 0 ? (
          <div className="text-zinc-500 text-sm py-4 text-center">No sources configured</div>
        ) : (
          sources.map((source) => (
            <div
              key={source.id}
              className={`flex items-center justify-between p-3 rounded-lg border ${
                source.enabled ? 'bg-zinc-800 border-zinc-700' : 'bg-zinc-900 border-zinc-800 opacity-60'
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-white truncate">{source.id}</span>
                  <span className={`px-1.5 py-0.5 text-xs rounded ${
                    source.source_type === 'docs' ? 'bg-blue-900 text-blue-300' :
                    source.source_type === 'jac' ? 'bg-purple-900 text-purple-300' :
                    'bg-cyan-900 text-cyan-300'
                  }`}>
                    {sourceTypeLabels[source.source_type]}
                  </span>
                </div>
                <div className="text-xs text-zinc-500 truncate mt-1">
                  {source.git_url} ({source.branch}:{source.path})
                </div>
              </div>
              <div className="flex items-center gap-2 ml-3">
                <button
                  onClick={() => onToggle(source.id)}
                  className={`px-2 py-1 text-xs rounded transition ${
                    source.enabled
                      ? 'bg-green-900 text-green-300 hover:bg-green-800'
                      : 'bg-zinc-700 text-zinc-400 hover:bg-zinc-600'
                  }`}
                >
                  {source.enabled ? 'Enabled' : 'Disabled'}
                </button>
                <button
                  onClick={() => onDelete(source.id)}
                  className="px-2 py-1 text-xs bg-red-900 text-red-300 hover:bg-red-800 rounded transition"
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
      </div>}
    </div>
  )
}

function FileEditor() {
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [content, setContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [modifiedFiles, setModifiedFiles] = useState(new Set())
  const saveTimeoutRef = useRef(null)

  const fetchFiles = async () => {
    try {
      const [configRes, promptsRes] = await Promise.all([
        fetch('/api/config'),
        fetch('/api/prompts')
      ])
      const configData = await configRes.json()
      const promptsData = await promptsRes.json()

      const fileList = [
        { name: 'config.yaml', type: 'config', language: 'yaml' },
        ...promptsData.map(p => ({
          name: p.filename,
          type: 'prompt',
          language: 'plaintext'
        }))
      ].sort((a, b) => {
        if (a.type === 'config') return -1
        if (b.type === 'config') return 1
        return a.name.localeCompare(b.name)
      })
      setFiles(fileList)

      if (fileList.length > 0 && !selectedFile) {
        loadFile(fileList[0])
      }
    } catch (err) {
      setError('Failed to load files')
    }
  }

  useEffect(() => {
    fetchFiles()
  }, [])

  const loadFile = async (file) => {
    try {
      let data
      if (file.type === 'config') {
        const res = await fetch('/api/config')
        data = await res.json()
      } else {
        const res = await fetch(`/api/prompts/${file.name}`)
        data = await res.json()
      }
      setContent(data.content)
      setOriginalContent(data.content)
      setSelectedFile(file)
      setError(null)
    } catch (err) {
      setError('Failed to load file')
    }
  }

  const saveFile = async () => {
    if (!selectedFile) return
    setSaving(true)
    setError(null)
    try {
      let res
      if (selectedFile.type === 'config') {
        res = await fetch('/api/config', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content })
        })
      } else {
        res = await fetch(`/api/prompts/${selectedFile.name}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content })
        })
      }
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail)
      }
      setOriginalContent(content)
      setModifiedFiles(prev => {
        const next = new Set(prev)
        next.delete(selectedFile.name)
        return next
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleEditorChange = (value) => {
    setContent(value || '')
    if (selectedFile) {
      const isModified = value !== originalContent
      setModifiedFiles(prev => {
        const next = new Set(prev)
        if (isModified) {
          next.add(selectedFile.name)
        } else {
          next.delete(selectedFile.name)
        }
        return next
      })

      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
      if (isModified) {
        saveTimeoutRef.current = setTimeout(() => {
          saveFile()
        }, 1000)
      }
    }
  }

  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [])

  return (
    <div className="bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden" style={{ height: 'calc(100vh - 180px)' }}>
      <div className="flex h-full">
        <div className="w-48 border-r border-zinc-800 bg-zinc-950 overflow-y-auto">
          <div className="p-2 text-xs text-zinc-500 uppercase tracking-wide border-b border-zinc-800">
            Files
          </div>
          {files.map((file) => (
            <button
              key={file.name}
              onClick={() => loadFile(file)}
              className={`w-full px-3 py-2 text-left text-sm truncate flex items-center gap-2 transition ${
                selectedFile?.name === file.name
                  ? 'bg-zinc-800 text-white'
                  : 'text-zinc-400 hover:bg-zinc-800 hover:text-white'
              }`}
            >
              <span className="flex-1 truncate">{file.name}</span>
              {modifiedFiles.has(file.name) && (
                <span className="w-2 h-2 rounded-full bg-yellow-500 flex-shrink-0" />
              )}
            </button>
          ))}
        </div>

        <div className="flex-1 flex flex-col">
          <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-900">
            <div className="flex items-center gap-3">
              <span className="text-sm text-white">{selectedFile?.name || 'No file selected'}</span>
              {saving && <span className="text-xs text-zinc-400">Saving...</span>}
            </div>
            {error && <span className="text-xs text-red-400">{error}</span>}
          </div>

          <div className="flex-1">
            {selectedFile && (
              <Editor
                height="100%"
                language={selectedFile.language}
                value={content}
                onChange={handleEditorChange}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  tabSize: 2,
                  automaticLayout: true,
                }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StageCard({ stage, stageKey, isActive, progress, onRun, disabled }) {
  const statusColors = {
    pending: 'bg-zinc-700',
    running: 'bg-blue-600 animate-pulse',
    complete: 'bg-green-600',
    error: 'bg-red-600',
  }

  const stageDescriptions = {
    fetch: 'Fetches docs from git sources, cleans markdown, extracts Jac skeletons',
    extract: 'Categorizes code examples, selects best examples per construct (no LLM)',
    assemble: 'Single LLM call to generate final reference document',
  }

  const showProgress = stage.status === 'running' && progress?.total > 0

  return (
    <div className={`rounded-lg border ${isActive ? 'border-blue-500 bg-zinc-800' : 'border-zinc-700 bg-zinc-900'}`}>
      <button
        onClick={() => onRun(stageKey)}
        disabled={disabled}
        className={`w-full px-3 py-2 text-xs font-medium rounded-t-lg border-b border-zinc-700 transition ${
          disabled
            ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
            : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-white cursor-pointer'
        }`}
      >
        Run Stage
      </button>
      <div className="p-4">
        <div className="mb-3">
          <h3 className="font-medium text-white">{stage.name}</h3>
          <p className="text-xs text-zinc-500 mt-1">{stageDescriptions[stageKey]}</p>
          <span className={`inline-block mt-2 px-2 py-0.5 rounded text-xs text-white ${statusColors[stage.status]}`}>
            {stage.status}
          </span>
        </div>

      {showProgress ? (
        <ProgressBar
          current={progress.current}
          total={progress.total}
          message={progress.message}
        />
      ) : (
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

          {stageKey === 'extract' && stage.extra?.signatures > 0 && (
            <>
              <div className="text-zinc-400">Signatures:</div>
              <div className="text-white">{stage.extra.signatures}</div>
              <div className="text-zinc-400">Examples:</div>
              <div className="text-white">{stage.extra.selected_examples || 0} selected</div>
            </>
          )}

          {stageKey !== 'extract' && (
            <>
              <div className="text-zinc-400">Files:</div>
              <div className="text-white">{stage.file_count || stage.files?.length || 0}</div>
            </>
          )}
        </div>
      )}

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
    progress: 'text-zinc-500',
  }

  if (event.event === 'progress') return null

  return (
    <div className="text-xs font-mono py-1 border-b border-zinc-800">
      <span className="text-zinc-500">{new Date(event.timestamp).toLocaleTimeString()}</span>
      <span className={`ml-2 ${colors[event.event] || 'text-white'}`}>{event.event}</span>
      {event.data?.stage && <span className="ml-2 text-zinc-400">[{event.data.stage}]</span>}
    </div>
  )
}

function App() {
  const [page, setPage] = useState('pipeline')
  const [connected, setConnected] = useState(false)
  const [running, setRunning] = useState(false)
  const [sources, setSources] = useState([])
  const [stages, setStages] = useState({
    fetch: { name: 'Fetch & Sanitize', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
    extract: { name: 'Deterministic Extract', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
    assemble: { name: 'LLM Assembly', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
  })
  const [progress, setProgress] = useState({})
  const [validation, setValidation] = useState(null)
  const [logs, setLogs] = useState([])
  const [metrics, setMetrics] = useState(null)
  const wsRef = useRef(null)
  const logsEndRef = useRef(null)

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

  const fetchStatus = async () => {
    try {
      const [statusRes, stagesRes] = await Promise.all([
        fetch('/api/status'),
        fetch('/api/stages')
      ])
      const status = await statusRes.json()
      const stagesData = await stagesRes.json()

      setRunning(status.is_running)

      if (stagesData.length > 0) {
        const stageKeys = ['fetch', 'extract', 'assemble']
        const newStages = {}
        stagesData.forEach((s, i) => {
          const key = stageKeys[i]
          if (key) {
            newStages[key] = {
              ...stages[key],
              ...s,
            }
          }
        })
        setStages(prev => ({ ...prev, ...newStages }))
      }

      if (status.is_running) {
        const metricsRes = await fetch('/api/metrics')
        const metricsData = await metricsRes.json()
        if (metricsData.validation) {
          setValidation(metricsData.validation)
        }
      }
    } catch (err) {
      console.error('Failed to fetch status:', err)
    }
  }

  useEffect(() => {
    fetchSources()
    fetchStatus()
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

        if (msg.event !== 'progress') {
          setLogs(prev => [...prev.slice(-99), msg])
        }

        if (msg.event === 'pipeline_start') {
          setRunning(true)
          setValidation(null)
          setProgress({})
        }

        if (msg.event === 'pipeline_complete') {
          setRunning(false)
          setProgress({})
          if (msg.data) setMetrics(msg.data)
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
    return () => {
      cancelled = true
      wsRef.current?.close()
    }
  }, [])

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const runPipeline = async () => {
    setLogs([])
    setStages({
      fetch: { name: 'Fetch & Sanitize', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
      extract: { name: 'Deterministic Extract', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
      assemble: { name: 'LLM Assembly', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
    })
    setValidation(null)
    setMetrics(null)
    setProgress({})

    try {
      await fetch('/api/run', { method: 'POST' })
    } catch (err) {
      console.error(err)
    }
  }

  const runStage = async (stageKey) => {
    try {
      await fetch(`/api/run/${stageKey}`, { method: 'POST' })
    } catch (err) {
      console.error(err)
    }
  }

  const activeStage = Object.keys(stages).find(k => stages[k].status === 'running')
  const totalInput = stages.fetch.input_size
  const totalOutput = stages.assemble.output_size
  const overallRatio = totalInput > 0 ? totalOutput / totalInput : 0

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-6">
            <div>
              <h1 className="text-2xl font-bold">Pipeline Dashboard</h1>
              <p className="text-zinc-500 text-sm">Documentation compression pipeline</p>
            </div>
            <div className="flex gap-1 bg-zinc-900 rounded-lg p-1">
              <button
                onClick={() => setPage('pipeline')}
                className={`px-4 py-1.5 text-sm rounded-md transition ${
                  page === 'pipeline' ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-white'
                }`}
              >
                Pipeline
              </button>
              <button
                onClick={() => setPage('config')}
                className={`px-4 py-1.5 text-sm rounded-md transition ${
                  page === 'config' ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-white'
                }`}
              >
                Config
              </button>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-zinc-400">{connected ? 'Connected' : 'Disconnected'}</span>
            {page === 'pipeline' && (
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
            )}
          </div>
        </div>

        {page === 'config' && (
          <>
            <SourcePanel
              sources={sources}
              onAdd={addSource}
              onDelete={deleteSource}
              onToggle={toggleSource}
              onRefresh={fetchSources}
            />
            <FileEditor />
          </>
        )}

        {page === 'pipeline' && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
              <div className="text-zinc-500 text-sm">Total Input</div>
              <div className="text-xl font-bold">{totalInput > 0 ? formatBytes(totalInput) : '-'}</div>
            </div>
            <div className="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
              <div className="text-zinc-500 text-sm">Total Output</div>
              <div className="text-xl font-bold">{totalOutput > 0 ? formatBytes(totalOutput) : '-'}</div>
            </div>
            <div className="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
              <div className="text-zinc-500 text-sm">Compression</div>
              <div className={`text-xl font-bold ${overallRatio > 0 && overallRatio < 0.05 ? 'text-green-400' : ''}`}>
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

        {page === 'pipeline' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {Object.entries(stages).map(([key, stage]) => (
                <StageCard
                  key={key}
                  stageKey={key}
                  stage={stage}
                  isActive={activeStage === key}
                  progress={progress[key]}
                  onRun={runStage}
                  disabled={running || !connected}
                />
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
          </>
        )}
      </div>
    </div>
  )
}

export default App
