import { useState } from 'react'
import EvaluationModal from '@/components/EvaluationModal'
import CompareModal from '@/components/CompareModal'
import type { TestFile, Stash } from '@/utils/types'
import { API_BASE, MODEL_DISPLAY_NAMES } from '@/utils/types'

interface Props {
  files: TestFile[]
  stashes: Stash[]
  onStash: () => void
  onClean: () => void
  onClearDb: () => void
  onRefresh: () => void
  onDelete?: (filePath: string) => void
}

export default function FileManager({
  files,
  stashes,
  onStash,
  onClean,
  onClearDb,
  onRefresh,
  onDelete
}: Props) {
  const [sortBy, setSortBy] = useState<'size' | 'modified' | 'model-variant'>(() => {
    const saved = localStorage.getItem('fileManager_sortBy')
    return (saved as any) || 'modified'
  })

  const handleSortChange = (newSort: 'size' | 'modified' | 'model-variant') => {
    setSortBy(newSort)
    localStorage.setItem('fileManager_sortBy', newSort)
  }

  const [stashSortBy, setStashSortBy] = useState<'created' | 'model-variant'>(() => {
    const saved = localStorage.getItem('fileManager_stashSortBy')
    return (saved as any) || 'created'
  })

  const handleStashSortChange = (newSort: 'created' | 'model-variant') => {
    setStashSortBy(newSort)
    localStorage.setItem('fileManager_stashSortBy', newSort)
  }

  const [expandedStashes, setExpandedStashes] = useState<Set<string>>(new Set())
  const [stashFiles, setStashFiles] = useState<Map<string, TestFile[]>>(new Map())
  const [showEvalModal, setShowEvalModal] = useState(false)
  const [evalResults, setEvalResults] = useState<any>(null)
  const [selectedStashForCompare, setSelectedStashForCompare] = useState<string | null>(null)
  const [showCompareModal, setShowCompareModal] = useState(false)
  const [compareResults, setCompareResults] = useState<any>(null)
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())
  const [selectedCollections, setSelectedCollections] = useState<Set<string>>(new Set())

  const downloadGraph = async (url: string, filename: string, format: 'svg' | 'png') => {
    try {
      const res = await fetch(`${url}?format=${format}`)
      const blob = await res.blob()
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = filename.replace(/\.(svg|png)$/, `.${format}`)
      link.click()
      URL.revokeObjectURL(link.href)
    } catch (error) {
      console.error('Failed to download graph:', error)
    }
  }

  const exportCollectionsGraph = (format: 'svg' | 'png') => {
    downloadGraph(`${API_BASE}/graph/collections`, `collections-benchmark.${format}`, format)
  }

  const toggleFileSelection = (runId: string) => {
    setSelectedFiles(prev => {
      const next = new Set(prev)
      if (next.has(runId)) {
        next.delete(runId)
      } else {
        next.add(runId)
      }
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedFiles.size === files.length) {
      setSelectedFiles(new Set())
    } else {
      setSelectedFiles(new Set(files.map(f => f.name)))
    }
  }

  const stashSelected = async () => {
    if (selectedFiles.size === 0) return
    try {
      const res = await fetch(`${API_BASE}/stash-selected`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_ids: Array.from(selectedFiles) })
      })
      if (res.ok) {
        setSelectedFiles(new Set())
        onRefresh()
      }
    } catch (error) {
      console.error('Failed to stash selected files:', error)
    }
  }

  const toggleCollectionSelection = (name: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedCollections(prev => {
      const next = new Set(prev)
      if (next.has(name)) {
        next.delete(name)
      } else {
        next.add(name)
      }
      return next
    })
  }

  const exportCollectionsCSV = async () => {
    if (selectedCollections.size === 0) return
    try {
      const res = await fetch(`${API_BASE}/export-collections-csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collections: Array.from(selectedCollections) })
      })
      if (res.ok) {
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `collections-export-${new Date().toISOString().split('T')[0]}.csv`
        link.click()
        URL.revokeObjectURL(url)
      }
    } catch (error) {
      console.error('Failed to export collections CSV:', error)
    }
  }

  const sortedFiles = [...files].sort((a, b) => {
    switch (sortBy) {
      case 'size':
        return b.size - a.size
      case 'modified':
        return b.modified - a.modified
      case 'model-variant': {
        // Use metadata from API if available
        const hasMetaA = a.metadata && a.metadata.model && a.metadata.variant
        const hasMetaB = b.metadata && b.metadata.model && b.metadata.variant

        // If neither has metadata, sort by name
        if (!hasMetaA && !hasMetaB) {
          return a.name.localeCompare(b.name)
        }

        // If only one has metadata, prioritize the one with metadata
        if (!hasMetaA) return 1
        if (!hasMetaB) return -1

        // Both have metadata - sort by model first
        const modelCompare = a.metadata!.model.localeCompare(b.metadata!.model)
        if (modelCompare !== 0) return modelCompare

        // Then by variant
        return a.metadata!.variant.localeCompare(b.metadata!.variant)
      }
      default:
        return 0
    }
  })

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString()
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  const toggleStash = async (stashName: string) => {
    const newExpanded = new Set(expandedStashes)

    if (newExpanded.has(stashName)) {
      newExpanded.delete(stashName)
    } else {
      newExpanded.add(stashName)

      if (!stashFiles.has(stashName)) {
        try {
          const res = await fetch(`${API_BASE}/stash/${stashName}/files`)
          const data = await res.json()
          setStashFiles(new Map(stashFiles.set(stashName, data.files || [])))
        } catch (error) {
          console.error(`Failed to fetch stash files for ${stashName}:`, error)
        }
    }
    }

    setExpandedStashes(newExpanded)
  }

  const deleteStash = async (stashName: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await fetch(`${API_BASE}/stash/${stashName}`, { method: 'DELETE' })
      onRefresh()
    } catch (error) {
      console.error(`Failed to delete stash ${stashName}:`, error)
    }
  }

  const evaluateStash = async (stashName: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const res = await fetch(`${API_BASE}/evaluate-collection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection: stashName })
      })
      const data = await res.json()
      if (data.status === 'success') {
        setEvalResults({ ...data, stashName })
        setShowEvalModal(true)
      }
    } catch (error) {
      console.error(`Failed to evaluate stash ${stashName}:`, error)
    }
  }

  const selectForCompare = (stashName: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedStashForCompare(stashName)
  }

  const compareWithSelected = async (stashName: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!selectedStashForCompare || selectedStashForCompare === stashName) return
    try {
      const res = await fetch(`${API_BASE}/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stash1: selectedStashForCompare, stash2: stashName })
      })
      const data = await res.json()
      if (data.status === 'success') {
        setCompareResults(data)
        setShowCompareModal(true)
      }
    } catch (error) {
      console.error(`Failed to compare stashes:`, error)
    }
  }

  return (
    <div className="bg-terminal-surface border border-terminal-border rounded p-6">
      <div className="flex justify-between items-center mb-6 pb-2 border-b border-terminal-border">
        <h2 className="text-terminal-accent text-xl m-0">Test Results</h2>
        <button onClick={onRefresh} className="px-3 py-2 bg-transparent border border-terminal-border rounded text-gray-400 text-sm hover:bg-zinc-800 hover:border-gray-600 hover:text-white cursor-pointer" title="Refresh">
          ↻
        </button>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap items-center justify-between">
        <div className="flex gap-2">
          <button onClick={onStash} className="px-4 py-2.5 bg-terminal-border text-gray-300 border border-gray-600 rounded text-sm font-semibold hover:bg-zinc-700 cursor-pointer">
            Stash All
          </button>
          {selectedFiles.size > 0 && (
            <button onClick={stashSelected} className="px-4 py-2.5 bg-blue-900 text-white border border-blue-700 rounded text-sm font-semibold hover:bg-blue-800 cursor-pointer">
              Stash Selected ({selectedFiles.size})
            </button>
          )}
          <div className="flex">
            <button onClick={() => exportCollectionsGraph('svg')} className="px-3 py-2.5 bg-blue-900 text-white border border-blue-700 rounded-l text-sm font-semibold hover:bg-blue-800 cursor-pointer">
              SVG
            </button>
            <button onClick={() => exportCollectionsGraph('png')} className="px-3 py-2.5 bg-blue-900 text-white border-l-0 border border-blue-700 rounded-r text-sm font-semibold hover:bg-blue-800 cursor-pointer">
              PNG
            </button>
          </div>
          <button onClick={onClean} className="px-4 py-2.5 bg-red-900 text-white rounded text-sm font-semibold hover:bg-red-800 cursor-pointer">
            Delete Uncategorized
          </button>
          <button onClick={() => {
            if (window.confirm('Are you sure you want to nuke the database? This will delete all benchmark results and cannot be undone.')) {
              onClearDb()
            }
          }} className="px-4 py-2.5 bg-red-950 text-white border border-red-800 rounded text-sm font-semibold hover:bg-red-900 cursor-pointer">
            Nuke Database
          </button>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-gray-400 text-sm">Sort by:</label>
          <select value={sortBy} onChange={e => handleSortChange(e.target.value as any)} className="px-2 py-1.5 bg-terminal-surface border border-terminal-border rounded text-gray-300 text-sm cursor-pointer focus:outline-none focus:border-terminal-accent">
            <option value="modified">Date Modified</option>
            <option value="model-variant">Model + Variant</option>
            <option value="size">Size</option>
          </select>
        </div>
      </div>

      <div className="max-h-[500px] overflow-y-auto mb-4">
        {sortedFiles.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 px-4 text-gray-500 text-center">
            <p className="text-base text-gray-400 mb-2">No uncategorized test files found</p>
            <span className="text-sm text-gray-600">Run a benchmark to generate test results</span>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 mb-2 px-3 py-2 bg-zinc-800 rounded">
              <input
                type="checkbox"
                checked={selectedFiles.size === files.length && files.length > 0}
                onChange={toggleSelectAll}
                className="w-4 h-4 cursor-pointer"
              />
              <span className="text-gray-400 text-sm">Select All</span>
            </div>
            {sortedFiles.map(file => (
              <div
                key={file.path}
                className={`grid grid-cols-[auto_1fr_auto] gap-4 items-center p-3 mb-2 rounded border bg-zinc-900 ${selectedFiles.has(file.name) ? 'border-blue-500' : 'border-terminal-border'}`}
              >
                <input
                  type="checkbox"
                  checked={selectedFiles.has(file.name)}
                  onChange={() => toggleFileSelection(file.name)}
                  className="w-4 h-4 cursor-pointer"
                />
                <div className="flex-1">
                  <div className="text-gray-300 font-medium mb-1 text-sm">{file.name}</div>
                  <div className="flex gap-4 text-xs text-gray-500">
                    <span>{formatSize(file.size)}</span>
                    <span>{formatDate(file.modified)}</span>
                  </div>
                </div>

                {onDelete && (
                  <button
                    onClick={() => onDelete(file.path)}
                    className="p-1.5 text-red-500 hover:text-red-400 hover:bg-red-950 border border-red-500 rounded transition-colors cursor-pointer"
                    title="Delete file"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </>
        )}
      </div>

      {files.length > 0 && (
        <div className="flex justify-between px-3 py-2.5 bg-zinc-900 rounded text-sm text-gray-400">
          <span>{files.length} file(s)</span>
          <span>
            Total: {formatSize(files.reduce((acc, f) => acc + f.size, 0))}
          </span>
        </div>
      )}

      {stashes.length > 0 && (
        <div className="mt-8">
          <div className="flex justify-between items-center mb-4 pb-2 border-b border-terminal-border">
            <h3 className="text-terminal-accent text-lg m-0">Collections</h3>
            <div className="flex items-center gap-4">
              {selectedCollections.size > 0 && (
                <button
                  onClick={exportCollectionsCSV}
                  className="px-3 py-1.5 bg-green-900 text-green-300 border border-green-700 rounded text-xs font-semibold hover:bg-green-800 cursor-pointer"
                >
                  Export CSV ({selectedCollections.size})
                </button>
              )}
              <div className="flex items-center gap-2">
                <label className="text-gray-400 text-sm">Sort by:</label>
                <select value={stashSortBy} onChange={e => handleStashSortChange(e.target.value as any)} className="px-2 py-1.5 bg-terminal-surface border border-terminal-border rounded text-gray-300 text-sm cursor-pointer focus:outline-none focus:border-terminal-accent">
                  <option value="created">Time Stashed</option>
                  <option value="model-variant">Model + Variant</option>
                </select>
              </div>
            </div>
          </div>
          {[...stashes].sort((a, b) => {
            switch (stashSortBy) {
              case 'created':
                return b.created - a.created
              case 'model-variant': {
                const hasMetaA = a.metadata && a.metadata.model && a.metadata.variant
                const hasMetaB = b.metadata && b.metadata.model && b.metadata.variant

                if (!hasMetaA && !hasMetaB) {
                  return a.name.localeCompare(b.name)
                }

                if (!hasMetaA) return 1
                if (!hasMetaB) return -1

                const modelCompare = a.metadata!.model.localeCompare(b.metadata!.model)
                if (modelCompare !== 0) return modelCompare

                return a.metadata!.variant.localeCompare(b.metadata!.variant)
              }
              default:
                return 0
            }
          }).map(stash => {
            const isExpanded = expandedStashes.has(stash.name)
            const files = stashFiles.get(stash.name) || []

            let metadata: { model: string; variant: string; tests: string; batchSize?: number } | null = null
            if (stash.metadata) {
              const displayModel = MODEL_DISPLAY_NAMES[stash.metadata.model] || stash.metadata.model
              const displayVariant = stash.metadata.variant.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())

              metadata = {
                model: displayModel,
                variant: displayVariant,
                tests: stash.metadata.total_tests,
                batchSize: stash.metadata.batch_size
              }
            }

            return (
              <div key={stash.name} className="mb-2">
                <div className={`px-4 py-3 bg-zinc-900 border rounded flex justify-between items-center ${selectedCollections.has(stash.name) ? 'border-green-500' : 'border-terminal-border'}`}>
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={selectedCollections.has(stash.name)}
                      onClick={(e) => toggleCollectionSelection(stash.name, e)}
                      onChange={() => {}}
                      className="w-4 h-4 cursor-pointer"
                    />
                    <button
                      onClick={() => toggleStash(stash.name)}
                      className="flex-1 text-left hover:opacity-80 transition-opacity cursor-pointer flex items-center gap-3"
                    >
                      <span className="text-gray-400 text-lg">{isExpanded ? '▼' : '▶'}</span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <div className="text-gray-300 font-medium text-sm">{stash.name}</div>
                        {metadata && (
                          <div className="flex items-center gap-2 text-xs text-gray-400">
                            <span>-</span>
                            <span className="text-blue-400 font-semibold">{metadata.model}</span>
                            <span>-</span>
                            <span className="text-purple-400 font-semibold">{metadata.variant}</span>
                            {metadata.batchSize && (
                              <>
                                <span>-</span>
                                <span className="text-cyan-400 font-semibold">batch {metadata.batchSize}</span>
                              </>
                            )}
                            <span>-</span>
                            <span className="text-terminal-accent font-semibold">x{stash.file_count}</span>
                          </div>
                        )}
                      </div>
                      <div className="text-gray-500 text-xs mt-1">
                        {stash.file_count} files • {formatDate(stash.created)}
                      </div>
                    </div>
                  </button>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={(e) => selectForCompare(stash.name, e)}
                      className={`px-3 py-1.5 rounded text-xs font-semibold cursor-pointer transition-all ${
                        selectedStashForCompare === stash.name
                          ? 'bg-blue-600 text-white border border-blue-600'
                          : 'bg-transparent text-blue-400 border border-blue-600 hover:bg-blue-900'
                      }`}
                      title="Select this stash for comparison"
                    >
                      Select for Compare
                    </button>
                    <button
                      onClick={(e) => compareWithSelected(stash.name, e)}
                      className="px-3 py-1.5 bg-transparent text-purple-400 border border-purple-600 rounded text-xs font-semibold hover:bg-purple-900 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Compare with selected stash"
                      disabled={!selectedStashForCompare || selectedStashForCompare === stash.name}
                    >
                      Compare with Selected
                    </button>
                    <button
                      onClick={(e) => evaluateStash(stash.name, e)}
                      className="px-3 py-1.5 bg-terminal-border text-terminal-accent border border-terminal-accent rounded text-xs font-semibold hover:bg-terminal-accent hover:text-black cursor-pointer"
                      title="Evaluate all files in this stash"
                    >
                      Evaluate All
                    </button>
                    <button
                      onClick={(e) => deleteStash(stash.name, e)}
                      className="p-1.5 text-red-500 hover:text-red-400 hover:bg-red-950 border border-red-500 rounded transition-colors cursor-pointer"
                      title="Delete entire stash"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="mt-2 ml-4 pl-4 border-l-2 border-terminal-border">
                    {files.length === 0 ? (
                      <div className="p-3 text-gray-500 text-sm">Loading...</div>
                    ) : (
                      files.map(file => (
                        <div
                          key={file.path}
                          className="grid grid-cols-[1fr_auto] gap-4 items-center p-3 mb-2 rounded border bg-zinc-900 border-terminal-border"
                        >
                          <div className="flex-1">
                            <div className="text-gray-300 font-medium mb-1 text-sm">{file.name}</div>
                            <div className="flex gap-4 text-xs text-gray-500">
                              <span>{formatSize(file.size)}</span>
                              <span>{formatDate(file.modified)}</span>
                            </div>
                          </div>

                          {onDelete && (
                            <button
                              onClick={() => onDelete(file.path)}
                              className="p-1.5 text-red-500 hover:text-red-400 hover:bg-red-950 border border-red-500 rounded transition-colors cursor-pointer"
                              title="Delete file"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <EvaluationModal
        isOpen={showEvalModal}
        onClose={() => setShowEvalModal(false)}
        results={evalResults}
      />
      <CompareModal
        isOpen={showCompareModal}
        onClose={() => setShowCompareModal(false)}
        results={compareResults}
      />
    </div>
  )
}
