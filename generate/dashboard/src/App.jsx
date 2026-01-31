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

function StagePipeline({ stages, progress, onRun, disabled }) {
  const stageOrder = ['fetch', 'extract', 'assemble']
  const stageNames = {
    fetch: 'Fetch & Sanitize',
    extract: 'Deterministic Extract',
    assemble: 'LLM Assembly',
  }

  const getStageProgress = (key) => {
    const stage = stages[key]
    if (stage.status === 'complete') return 100
    if (stage.status === 'error') return 100
    if (stage.status === 'running' && progress[key]?.total > 0) {
      return (progress[key].current / progress[key].total) * 100
    }
    if (stage.status === 'running') return 50
    return 0
  }

  return (
    <div className="mb-6">
      <div className="flex items-stretch h-44">
        {stageOrder.map((key, index) => {
          const stage = stages[key]
          const stageProgress = getStageProgress(key)
          const isRunning = stage.status === 'running'
          const isComplete = stage.status === 'complete'
          const isError = stage.status === 'error'
          const isPending = stage.status === 'pending'
          const showProgress = isRunning && progress[key]?.total > 0

          return (
            <div
              key={key}
              className={`stage-arrow relative flex-1 transition-all duration-300 ${
                isRunning ? 'stage-running' : ''
              }`}
              style={{ marginLeft: index === 0 ? 0 : '-12px' }}
            >
              <div className="absolute inset-0 bg-zinc-800 stage-arrow-inner border-r border-zinc-700/50" />

              <div className={`absolute inset-0 stage-arrow-inner overflow-hidden ${
                isError ? 'bg-red-900/80' : ''
              }`}>
                <div
                  className={`absolute inset-0 stage-fill ${
                    isComplete ? 'stage-fill-complete' : 'stage-fill-animated'
                  } ${isRunning ? 'stage-shimmer' : ''}`}
                  style={{
                    clipPath: `inset(0 ${100 - stageProgress}% 0 0)`,
                    transition: 'clip-path 0.4s ease-out',
                  }}
                />
              </div>

              <div
                className="absolute inset-0 flex flex-col z-10 py-3"
                style={{
                  paddingLeft: index === 0 ? '16px' : '28px',
                  paddingRight: index === 2 ? '16px' : '28px'
                }}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 stage-text">
                    <span className="text-xs text-zinc-300 font-jetbrains">{index + 1}</span>
                    <span className="text-sm font-semibold font-jetbrains text-white">
                      {stageNames[key]}
                    </span>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); onRun(key); }}
                    disabled={disabled}
                    className={`stage-button px-3 py-1.5 text-xs font-jetbrains font-medium rounded transition ${
                      disabled
                        ? 'opacity-50 cursor-not-allowed text-zinc-400'
                        : 'text-white cursor-pointer'
                    }`}
                  >
                    {isRunning ? 'Running...' : 'Run'}
                  </button>
                </div>

                {showProgress ? (
                  <div className="flex-1 flex flex-col justify-center font-jetbrains stage-text">
                    <div className="text-xs text-white mb-1 truncate">
                      {progress[key].message || 'Processing...'}
                    </div>
                    <div className="h-1.5 bg-black/40 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-white transition-all duration-200"
                        style={{ width: `${stageProgress}%` }}
                      />
                    </div>
                    <div className="text-xs text-white mt-1">
                      {progress[key].current} / {progress[key].total}
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 grid grid-cols-2 gap-x-4 gap-y-1 text-xs content-center font-jetbrains stage-text">
                    <div className="text-zinc-300">Input</div>
                    <div className="text-white">{stage.input_size > 0 ? formatBytes(stage.input_size) : '-'}</div>
                    <div className="text-zinc-300">Output</div>
                    <div className="text-white">{stage.output_size > 0 ? formatBytes(stage.output_size) : '-'}</div>
                    <div className="text-zinc-300">Ratio</div>
                    <div className={stage.compression_ratio < 0.5 && stage.compression_ratio > 0 ? 'text-green-300' : 'text-white'}>
                      {stage.input_size > 0 ? `${(stage.compression_ratio * 100).toFixed(0)}%` : '-'}
                    </div>
                    <div className="text-zinc-300">Duration</div>
                    <div className="text-white">{formatDuration(stage.duration)}</div>
                    {key === 'extract' && stage.extra?.signatures > 0 && (
                      <>
                        <div className="text-zinc-300">Signatures</div>
                        <div className="text-white">{stage.extra.signatures}</div>
                      </>
                    )}
                    {key !== 'extract' && (
                      <>
                        <div className="text-zinc-300">Files</div>
                        <div className="text-white">{stage.file_count || stage.files?.length || 0}</div>
                      </>
                    )}
                  </div>
                )}

                {isError && stage.error && (
                  <div className="text-xs text-red-200 mt-1 truncate stage-text font-jetbrains">{stage.error}</div>
                )}
              </div>
            </div>
          )
        })}
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
    <div className="bg-zinc-900/60 rounded-lg border border-zinc-800/50 mb-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2.5 flex items-center justify-between text-left hover:bg-zinc-800/50 rounded-lg transition"
      >
        <div className="flex items-center gap-3">
          <span className={`text-zinc-500 text-xs transition-transform ${expanded ? 'rotate-90' : ''}`}>&gt;</span>
          <h3 className="text-sm font-medium text-zinc-300">Sources</h3>
          <span className="text-xs text-zinc-600">({enabledCount} enabled)</span>
        </div>
        <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={onRefresh}
            className="stage-button px-2.5 py-1 text-xs text-zinc-300 rounded transition"
          >
            Refresh
          </button>
          <button
            onClick={() => { setShowForm(!showForm); setExpanded(true) }}
            className="stage-button px-2.5 py-1 text-xs text-white rounded transition"
          >
            {showForm ? 'Cancel' : 'Add'}
          </button>
        </div>
      </button>

      {expanded && <div className="px-3 pb-3">
      {showForm && (
        <form onSubmit={handleSubmit} className="mb-3 p-3 bg-zinc-800/50 rounded-lg border border-zinc-700/50">
          {error && (
            <div className="mb-3 p-2 bg-red-900/30 text-red-300 text-xs rounded border border-red-800/50">
              {error}
            </div>
          )}
          <div className="grid grid-cols-2 gap-2">
            <div className="col-span-2">
              <label className="block text-xs text-zinc-500 mb-1">ID</label>
              <input
                type="text"
                value={formData.id}
                onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                placeholder="my-source"
                className="w-full px-2 py-1.5 text-xs bg-zinc-900/80 border border-zinc-700/50 rounded text-white placeholder-zinc-600"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-zinc-500 mb-1">Git URL</label>
              <input
                type="text"
                value={formData.git_url}
                onChange={(e) => setFormData({ ...formData, git_url: e.target.value })}
                placeholder="https://github.com/user/repo.git"
                className="w-full px-2 py-1.5 text-xs bg-zinc-900/80 border border-zinc-700/50 rounded text-white placeholder-zinc-600"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Branch</label>
              <input
                type="text"
                value={formData.branch}
                onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                placeholder="main"
                className="w-full px-2 py-1.5 text-xs bg-zinc-900/80 border border-zinc-700/50 rounded text-white placeholder-zinc-600"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Path</label>
              <input
                type="text"
                value={formData.path}
                onChange={(e) => setFormData({ ...formData, path: e.target.value })}
                placeholder="docs/"
                className="w-full px-2 py-1.5 text-xs bg-zinc-900/80 border border-zinc-700/50 rounded text-white placeholder-zinc-600"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Type</label>
              <select
                value={formData.source_type}
                onChange={(e) => setFormData({ ...formData, source_type: e.target.value })}
                className="w-full px-2 py-1.5 text-xs bg-zinc-900/80 border border-zinc-700/50 rounded text-white"
              >
                <option value="docs">Documentation (.md)</option>
                <option value="jac">Jac Code (.jac)</option>
                <option value="both">Both</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                className="w-full px-3 py-1.5 text-xs bg-emerald-800/60 hover:bg-emerald-700/60 text-emerald-200 rounded transition border border-emerald-700/50"
              >
                Add Source
              </button>
            </div>
          </div>
        </form>
      )}

      <div className="space-y-1.5">
        {sources.length === 0 ? (
          <div className="text-zinc-600 text-xs py-4 text-center">No sources configured</div>
        ) : (
          sources.map((source) => (
            <div
              key={source.id}
              className={`flex items-center justify-between p-2.5 rounded-lg border ${
                source.enabled ? 'bg-zinc-800/40 border-zinc-700/50' : 'bg-zinc-900/40 border-zinc-800/30 opacity-50'
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-white truncate">{source.id}</span>
                  <span className={`px-1.5 py-0.5 text-xs rounded ${
                    source.source_type === 'docs' ? 'bg-sky-900/40 text-sky-300/80 border border-sky-800/30' :
                    source.source_type === 'jac' ? 'bg-violet-900/40 text-violet-300/80 border border-violet-800/30' :
                    'bg-teal-900/40 text-teal-300/80 border border-teal-800/30'
                  }`}>
                    {sourceTypeLabels[source.source_type]}
                  </span>
                </div>
                <div className="text-xs text-zinc-600 truncate mt-0.5">
                  {source.git_url} ({source.branch}:{source.path})
                </div>
              </div>
              <div className="flex items-center gap-1.5 ml-3">
                <button
                  onClick={() => onToggle(source.id)}
                  className={`px-2 py-1 text-xs rounded transition border ${
                    source.enabled
                      ? 'bg-emerald-900/30 text-emerald-300/80 border-emerald-800/30 hover:bg-emerald-800/40'
                      : 'bg-zinc-800/50 text-zinc-500 border-zinc-700/30 hover:bg-zinc-700/50'
                  }`}
                >
                  {source.enabled ? 'Enabled' : 'Disabled'}
                </button>
                <button
                  onClick={() => onDelete(source.id)}
                  className="px-2 py-1 text-xs bg-red-900/30 text-red-300/80 border border-red-800/30 hover:bg-red-800/40 rounded transition"
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
    <div className="bg-zinc-900/60 rounded-lg border border-zinc-800/50 overflow-hidden flex-1 min-h-0">
      <div className="flex h-full">
        <div className="w-44 border-r border-zinc-800/50 bg-zinc-950/50 overflow-y-auto">
          <div className="p-2 text-xs text-zinc-600 uppercase tracking-wider border-b border-zinc-800/50">
            Files
          </div>
          {files.map((file) => (
            <button
              key={file.name}
              onClick={() => loadFile(file)}
              className={`w-full px-3 py-1.5 text-left text-xs truncate flex items-center gap-2 transition ${
                selectedFile?.name === file.name
                  ? 'bg-zinc-800/60 text-white'
                  : 'text-zinc-500 hover:bg-zinc-800/40 hover:text-zinc-300'
              }`}
            >
              <span className="flex-1 truncate">{file.name}</span>
              {modifiedFiles.has(file.name) && (
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400/80 flex-shrink-0" />
              )}
            </button>
          ))}
        </div>

        <div className="flex-1 flex flex-col">
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-zinc-800/50 bg-zinc-900/40">
            <div className="flex items-center gap-3">
              <span className="text-xs text-zinc-300">{selectedFile?.name || 'No file selected'}</span>
              {saving && <span className="text-xs text-zinc-500">Saving...</span>}
            </div>
            {error && <span className="text-xs text-red-400/80">{error}</span>}
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
                  fontSize: 12,
                  fontFamily: "'JetBrains Mono', monospace",
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

function ValidationCard({ validation }) {
  if (!validation) return null

  const formatTokens = (count) => {
    if (count >= 1000) return `${(count / 1000).toFixed(1)}k`
    return count
  }

  return (
    <div className={`p-3 rounded-lg border ${validation.is_valid ? 'border-emerald-700/50 bg-emerald-900/10' : 'border-amber-700/50 bg-amber-900/10'}`}>
      <h3 className="text-xs font-medium text-zinc-400 mb-2">Validation</h3>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="text-zinc-500">Status</div>
        <div className={validation.is_valid ? 'text-emerald-400' : 'text-amber-400'}>
          {validation.is_valid ? 'PASSED' : 'WARNINGS'}
        </div>
        <div className="text-zinc-500">Patterns</div>
        <div className="text-white">{validation.patterns_found}/{validation.patterns_total}</div>
        {validation.output_size > 0 && (
          <>
            <div className="text-zinc-500">Output Size</div>
            <div className="text-white">{formatBytes(validation.output_size)}</div>
          </>
        )}
        {validation.token_count > 0 && (
          <>
            <div className="text-zinc-500">Tokens</div>
            <div className="text-white">{formatTokens(validation.token_count)}</div>
          </>
        )}
      </div>
      {validation.missing_patterns?.length > 0 && (
        <div className="mt-2 text-xs text-amber-400/80">
          Missing: {validation.missing_patterns.join(', ')}
        </div>
      )}
      {validation.issues?.length > 0 && (
        <div className="mt-2 text-xs text-amber-400/80">
          {validation.issues.join(', ')}
        </div>
      )}
    </div>
  )
}

function LogEntry({ event }) {
  const colors = {
    pipeline_start: 'text-sky-400/80',
    pipeline_complete: 'text-emerald-400/80',
    pipeline_error: 'text-red-400/80',
    stage_start: 'text-sky-300/80',
    stage_complete: 'text-emerald-300/80',
    stage_error: 'text-red-300/80',
    progress: 'text-zinc-600',
  }

  if (event.event === 'progress') return null

  return (
    <div className="text-xs py-1 border-b border-zinc-800/50">
      <span className="text-zinc-600">{new Date(event.timestamp).toLocaleTimeString()}</span>
      <span className={`ml-2 ${colors[event.event] || 'text-zinc-300'}`}>{event.event}</span>
      {event.data?.stage && <span className="ml-2 text-zinc-500">[{event.data.stage}]</span>}
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
  const [streamingText, setStreamingText] = useState('')
  const wsRef = useRef(null)
  const logsEndRef = useRef(null)
  const streamingRef = useRef(null)

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
          if (msg.data.stage === 'assemble') {
            setStreamingText('')
          }
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

  useEffect(() => {
    if (streamingRef.current) {
      streamingRef.current.scrollTop = streamingRef.current.scrollHeight
    }
  }, [streamingText])

  const runPipeline = async () => {
    setRunning(true)
    setLogs([])
    setStages({
      fetch: { name: 'Fetch & Sanitize', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
      extract: { name: 'Deterministic Extract', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
      assemble: { name: 'LLM Assembly', status: 'pending', input_size: 0, output_size: 0, files: [], compression_ratio: 1, extra: {} },
    })
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

  const activeStage = Object.keys(stages).find(k => stages[k].status === 'running')
  const totalInput = stages.fetch.input_size
  const totalOutput = stages.assemble.output_size
  const overallRatio = totalInput > 0 ? totalOutput / totalInput : 0

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-6 font-jetbrains">
      <div className="max-w-6xl mx-auto">
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
                onClick={runPipeline}
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

        {page === 'config' && (
          <div className="flex flex-col" style={{ height: 'calc(100vh - 120px)' }}>
            <SourcePanel
              sources={sources}
              onAdd={addSource}
              onDelete={deleteSource}
              onToggle={toggleSource}
              onRefresh={fetchSources}
            />
            <FileEditor />
          </div>
        )}

        {page === 'pipeline' && (
          <div className="grid grid-cols-4 gap-3 mb-6">
            <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800/50">
              <div className="text-zinc-500 text-xs mb-1">Total Input</div>
              <div className="text-lg font-semibold">{totalInput > 0 ? formatBytes(totalInput) : '-'}</div>
            </div>
            <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800/50">
              <div className="text-zinc-500 text-xs mb-1">Total Output</div>
              <div className="text-lg font-semibold">{totalOutput > 0 ? formatBytes(totalOutput) : '-'}</div>
            </div>
            <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800/50">
              <div className="text-zinc-500 text-xs mb-1">Compression</div>
              <div className={`text-lg font-semibold ${overallRatio > 0 && overallRatio < 0.05 ? 'text-emerald-400' : ''}`}>
                {overallRatio > 0 ? `${(overallRatio * 100).toFixed(2)}%` : '-'}
              </div>
            </div>
            <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800/50">
              <div className="text-zinc-500 text-xs mb-1">Duration</div>
              <div className="text-lg font-semibold">
                {metrics?.total_duration ? formatDuration(metrics.total_duration) : '-'}
              </div>
            </div>
          </div>
        )}

        {page === 'pipeline' && (
          <>
            <StagePipeline
              stages={stages}
              progress={progress}
              onRun={runStage}
              disabled={running || !connected}
            />

            {stages.assemble.status === 'running' && streamingText && (
              <div className="mb-3 p-3 bg-zinc-900/60 rounded-lg border border-zinc-800/50">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-medium text-zinc-400">LLM Output (streaming)</h3>
                  <span className="text-xs text-zinc-500">{streamingText.length.toLocaleString()} chars</span>
                </div>
                <div
                  ref={streamingRef}
                  className="h-48 overflow-y-auto bg-zinc-950/50 rounded p-2 font-mono text-xs text-zinc-300 whitespace-pre-wrap"
                >
                  {streamingText}
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <ValidationCard validation={validation} />

              <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800/50">
                <h3 className="text-xs font-medium text-zinc-400 mb-2">Event Log</h3>
                <div className="h-48 overflow-y-auto bg-zinc-950/50 rounded p-2">
                  {logs.length === 0 ? (
                    <div className="text-zinc-600 text-xs">No events yet</div>
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
