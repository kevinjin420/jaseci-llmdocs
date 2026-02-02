import { useState, useEffect, useRef } from 'react'
import Editor from '@monaco-editor/react'

export default function FileEditor() {
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [content, setContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [modifiedFiles, setModifiedFiles] = useState(new Set())
  const saveTimeoutRef = useRef(null)

  useEffect(() => {
    let mounted = true

    const init = async () => {
      try {
        const [configRes, promptsRes] = await Promise.all([
          fetch('/api/config'),
          fetch('/api/prompts')
        ])
        if (!mounted) return

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

        if (fileList.length > 0) {
          const firstFile = fileList[0]
          let data
          if (firstFile.type === 'config') {
            data = await configRes.json()
          } else {
            const res = await fetch(`/api/prompts/${firstFile.name}`)
            data = await res.json()
          }
          if (!mounted) return
          setContent(data.content)
          setOriginalContent(data.content)
          setSelectedFile(firstFile)
        }
      } catch {
        if (mounted) setError('Failed to load files')
      }
    }

    init()
    return () => { mounted = false }
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
    } catch {
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
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400/80 shrink-0" />
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
