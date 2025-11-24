import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import BenchmarkView from '@/views/BenchmarkView'
import FileManager from '@/views/FileManager'
import StatsPanel from '@/views/StatsPanel'

const API_BASE = 'http://localhost:5050/api'

interface Model {
  id: string
  name: string
  context_length: number
  pricing?: {
    prompt: string | number
    completion: string | number
  }
  architecture?: {
    tokenizer?: string
    input_modalities?: string[]
    output_modalities?: string[]
  }
}

interface Variant {
  name: string
  file: string
  size: number
  size_kb: number
}

interface TestFile {
  name: string
  path: string
  size: number
  modified: number
  metadata?: {
    model: string
    model_full: string
    variant: string
    test_suite: string
    total_tests: string
    batch_size?: number
    num_batches?: number
  }
}

interface Stash {
  name: string
  path: string
  file_count: number
  created: number
  metadata?: {
    model: string
    model_full: string
    variant: string
    test_suite: string
    total_tests: string
  }
}

function AppContent() {
  const [models, setModels] = useState<Model[]>([])
  const [variants, setVariants] = useState<Variant[]>([])
  const [testFiles, setTestFiles] = useState<TestFile[]>([])
  const [stashes, setStashes] = useState<Stash[]>([])
  const [apiKeys, setApiKeys] = useState<any>({})
  const [stats, setStats] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const location = useLocation()

  useEffect(() => {
    Promise.all([
      fetchModels(),
      fetchVariants(),
      fetchTestFiles(),
      fetchStashes(),
      fetchEnvStatus(),
      fetchStats()
    ]).finally(() => setIsLoading(false))
  }, [])

  const fetchModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/models`)
      const data = await res.json()
      setModels(data.models || [])
    } catch (error) {
      console.error('Failed to fetch models:', error)
    }
  }

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

  const fetchEnvStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/env-status`)
      const data = await res.json()
      setApiKeys(data.keys || {})
    } catch (error) {
      console.error('Failed to fetch env status:', error)
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
          <h1 className="text-terminal-accent text-xl font-semibold">Jac Benchmark Control Panel</h1>

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
              path="/statistics"
              element={
                stats ? (
                  <StatsPanel stats={stats} apiKeys={apiKeys} />
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
