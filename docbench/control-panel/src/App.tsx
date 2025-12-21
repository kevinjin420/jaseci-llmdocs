import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import BenchmarkView from '@/views/BenchmarkView'
import FileManager from '@/views/FileManager'
import StatsPanel from '@/views/StatsPanel'
import VariantsView from '@/views/VariantsView'
import type { Model, Variant, TestFile, Stash } from '@/utils/types'
import { API_BASE } from '@/utils/types'

function AppContent() {
  const [models, setModels] = useState<Model[]>([])
  const [variants, setVariants] = useState<Variant[]>([])
  const [testFiles, setTestFiles] = useState<TestFile[]>([])
  const [stashes, setStashes] = useState<Stash[]>([])
  const [stats, setStats] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [openRouterKey, setOpenRouterKey] = useState(() => localStorage.getItem('openRouterApiKey') || '')
  const [keyError, setKeyError] = useState('')
  const location = useLocation()

  const handleApiKeyChange = (key: string) => {
    setOpenRouterKey(key)
    if (key) {
      localStorage.setItem('openRouterApiKey', key)
    } else {
      localStorage.removeItem('openRouterApiKey')
    }
    setKeyError('')
  }

  const fetchModels = async (apiKey?: string) => {
    const key = apiKey ?? openRouterKey
    if (!key) {
      setModels([])
      return
    }
    try {
      const res = await fetch(`${API_BASE}/models`, { headers: { 'X-API-Key': key } })
      const data = await res.json()
      if (data.error) {
        setKeyError(data.error)
        setModels([])
      } else {
        setKeyError('')
        setModels(data.models || [])
      }
    } catch (error) {
      console.error('Failed to fetch models:', error)
    }
  }

  useEffect(() => {
    const savedKey = localStorage.getItem('openRouterApiKey') || ''
    Promise.all([
      fetchModels(savedKey),
      fetchVariants(),
      fetchTestFiles(),
      fetchStashes(),
      fetchStats()
    ]).finally(() => setIsLoading(false))
  }, [])

  useEffect(() => {
    if (openRouterKey) {
      fetchModels(openRouterKey)
    }
  }, [openRouterKey])

  const fetchVariants = async () => {
    try {
      const res = await fetch(`${API_BASE}/variants`)
      const data = await res.json()
      setVariants(data.variants || [])
    } catch (error) {
      console.error('Failed to fetch variants:', error)
    }
  }

  const fetchTestFiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/test-files`)
      const data = await res.json()
      setTestFiles(data.files || [])
    } catch (error) {
      console.error('Failed to fetch test files:', error)
    }
  }

  const fetchStashes = async () => {
    try {
      const res = await fetch(`${API_BASE}/stashes`)
      const data = await res.json()
      setStashes(data.stashes || [])
    } catch (error) {
      console.error('Failed to fetch stashes:', error)
    }
  }

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`)
      const data = await res.json()
      setStats(data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const stashResults = async () => {
    try {
      await fetch(`${API_BASE}/stash`, { method: 'POST' })
      await fetchTestFiles()
      await fetchStashes()
    } catch (error) {
      console.error('Failed to stash results:', error)
    }
  }

  const cleanResults = async () => {
    try {
      await fetch(`${API_BASE}/clean`, { method: 'POST' })
      await fetchTestFiles()
      await fetchStashes()
    } catch (error) {
      console.error('Failed to clean results:', error)
    }
  }

  const clearDatabase = async () => {
    try {
      await fetch(`${API_BASE}/clear-db`, { method: 'POST' })
      await fetchTestFiles()
      await fetchStashes()
    } catch (error) {
      console.error('Failed to clear database:', error)
    }
  }

  const deleteFile = async (filePath: string) => {
    try {
      await fetch(`${API_BASE}/delete-file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: filePath })
      })
      await fetchTestFiles()
    } catch (error) {
      console.error('Failed to delete file:', error)
    }
  }

  const handleBenchmarkComplete = () => {
    fetchTestFiles()
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-terminal-bg">
        <div className="text-center">
          <div className="w-10 h-10 mx-auto mb-4 border-3 border-terminal-border border-t-terminal-accent rounded-full animate-spin"></div>
          <p className="text-gray-400">Loading Control Panel...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-terminal-bg text-gray-300">
      <header className="bg-terminal-surface border-b border-terminal-border px-8 py-4">
        <div className="max-w-screen-2xl mx-auto flex justify-between items-center">
          <h1 className="text-terminal-accent text-xl font-semibold">Jaseci DocBench</h1>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-gray-400 text-sm">API Key:</label>
              <input
                type="password"
                value={openRouterKey}
                onChange={(e) => handleApiKeyChange(e.target.value)}
                placeholder="OpenRouter API Key"
                className={`w-64 px-3 py-1.5 bg-zinc-900 border rounded text-sm text-gray-300 focus:outline-none focus:border-terminal-accent ${keyError ? 'border-red-500' : 'border-terminal-border'}`}
              />
              {keyError && <span className="text-red-500 text-xs">{keyError}</span>}
              {openRouterKey && models.length > 0 && <span className="text-green-500 text-xs">Connected</span>}
            </div>
          </div>

          <nav className="flex gap-2">
            <Link
              to="/"
              className={`px-5 py-2.5 rounded border text-sm transition-all cursor-pointer ${
                location.pathname === '/'
                  ? 'bg-zinc-800 border-terminal-accent text-terminal-accent'
                  : 'border-terminal-border text-gray-400 hover:bg-zinc-800 hover:border-gray-600 hover:text-white'
              }`}
            >
              Benchmark
            </Link>
            <Link
              to="/files"
              className={`px-5 py-2.5 rounded border text-sm transition-all cursor-pointer ${
                location.pathname === '/files'
                  ? 'bg-zinc-800 border-terminal-accent text-terminal-accent'
                  : 'border-terminal-border text-gray-400 hover:bg-zinc-800 hover:border-gray-600 hover:text-white'
              }`}
            >
              Files
              {testFiles.length > 0 && (
                <span className="ml-1.5 bg-terminal-accent text-black px-1.5 py-0.5 rounded text-xs font-semibold">
                  {testFiles.length}
                </span>
              )}
            </Link>
            <Link
              to="/variants"
              className={`px-5 py-2.5 rounded border text-sm transition-all cursor-pointer ${
                location.pathname === '/variants'
                  ? 'bg-zinc-800 border-terminal-accent text-terminal-accent'
                  : 'border-terminal-border text-gray-400 hover:bg-zinc-800 hover:border-gray-600 hover:text-white'
              }`}
            >
              Variants
              {variants.length > 0 && (
                <span className="ml-1.5 bg-terminal-accent text-black px-1.5 py-0.5 rounded text-xs font-semibold">
                  {variants.length}
                </span>
              )}
            </Link>
            <Link
              to="/statistics"
              className={`px-5 py-2.5 rounded border text-sm transition-all cursor-pointer ${
                location.pathname === '/statistics'
                  ? 'bg-zinc-800 border-terminal-accent text-terminal-accent'
                  : 'border-terminal-border text-gray-400 hover:bg-zinc-800 hover:border-gray-600 hover:text-white'
              }`}
            >
              Statistics
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 p-8">
        <div className="max-w-screen-2xl mx-auto">
          <Routes>
            <Route
              path="/"
              element={
                <BenchmarkView
                  models={models}
                  variants={variants}
                  testFiles={testFiles}
                  onBenchmarkComplete={handleBenchmarkComplete}
                  apiKey={openRouterKey}
                />
              }
            />
            <Route
              path="/files"
              element={
                <FileManager
                  files={testFiles}
                  stashes={stashes}
                  onStash={stashResults}
                  onClean={cleanResults}
                  onClearDb={clearDatabase}
                  onRefresh={() => {
                    fetchTestFiles()
                    fetchStashes()
                  }}
                  onDelete={deleteFile}
                />
              }
            />
            <Route
              path="/variants"
              element={
                <VariantsView
                  variants={variants}
                  onRefresh={fetchVariants}
                />
              }
            />
            <Route
              path="/statistics"
              element={
                stats ? (
                  <StatsPanel stats={stats} apiKeyConfigured={!!openRouterKey && models.length > 0} />
                ) : (
                  <div className="bg-terminal-surface border border-terminal-border rounded p-12 text-center">
                    <h3 className="text-gray-300 text-xl mb-2">Loading Statistics...</h3>
                  </div>
                )
              }
            />
          </Routes>
        </div>
      </main>

      <footer className="bg-terminal-surface border-t border-terminal-border px-8 py-3">
        <div className="max-w-screen-2xl mx-auto flex justify-center gap-4 text-sm text-gray-600">
          <span>Jac Language LLM Documentation Benchmark Suite</span>
          <span>•</span>
          <span>Backend: {window.location.hostname}:5050</span>
        </div>
      </footer>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  )
}

export default App
