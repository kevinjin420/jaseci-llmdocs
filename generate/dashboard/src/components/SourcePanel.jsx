import { useState } from 'react'

export default function SourcePanel({ sources, onAdd, onDelete, onToggle, onRefresh, onEdit }) {
  const [expanded, setExpanded] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editingSource, setEditingSource] = useState(null)
  const [formData, setFormData] = useState({
    id: '',
    git_url: '',
    branch: 'main',
    path: '.',
    source_type: 'docs',
  })
  const [error, setError] = useState(null)

  const startEdit = (source) => {
    setEditingSource(source.id)
    setFormData({
      id: source.id,
      git_url: source.git_url,
      branch: source.branch,
      path: source.path,
      source_type: source.source_type,
    })
    setShowForm(false)
    setExpanded(true)
    setError(null)
  }

  const cancelEdit = () => {
    setEditingSource(null)
    setFormData({
      id: '',
      git_url: '',
      branch: 'main',
      path: '.',
      source_type: 'docs',
    })
    setError(null)
  }

  const handleEdit = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      await onEdit(editingSource, {
        git_url: formData.git_url,
        branch: formData.branch,
        path: formData.path,
        source_type: formData.source_type,
      })
      cancelEdit()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    if (!formData.id || !formData.git_url) {
      setError('ID and Git URL are required')
      return
    }
    try {
      await onAdd(formData)
      setFormData({ id: '', git_url: '', branch: 'main', path: '.', source_type: 'docs' })
      setShowForm(false)
      setEditingSource(null)
    } catch (err) {
      setError(err.message)
    }
  }

  const sourceTypeLabels = { docs: 'Documentation', jac: 'Jac Code', both: 'Both' }
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
          <button onClick={onRefresh} className="stage-button px-2.5 py-1 text-xs text-zinc-300 rounded transition">
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

      {expanded && (
        <div className="px-3 pb-3">
          {showForm && <SourceForm formData={formData} setFormData={setFormData} onSubmit={handleSubmit} error={error} />}
          <div className="space-y-1.5">
            {sources.length === 0 ? (
              <div className="text-zinc-600 text-xs py-4 text-center">No sources configured</div>
            ) : (
              sources.map((source) => (
                editingSource === source.id ? (
                  <EditSourceForm
                    key={source.id}
                    source={source}
                    formData={formData}
                    setFormData={setFormData}
                    onSubmit={handleEdit}
                    onCancel={cancelEdit}
                    error={error}
                  />
                ) : (
                  <SourceItem
                    key={source.id}
                    source={source}
                    sourceTypeLabels={sourceTypeLabels}
                    onEdit={() => startEdit(source)}
                    onToggle={() => onToggle(source.id)}
                    onDelete={() => onDelete(source.id)}
                  />
                )
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function SourceForm({ formData, setFormData, onSubmit, error }) {
  return (
    <form onSubmit={onSubmit} className="mb-3 p-3 bg-zinc-800/50 rounded-lg border border-zinc-700/50">
      {error && <div className="mb-3 p-2 bg-red-900/30 text-red-300 text-xs rounded border border-red-800/50">{error}</div>}
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
  )
}

function EditSourceForm({ source, formData, setFormData, onSubmit, onCancel, error }) {
  return (
    <form onSubmit={onSubmit} className="p-3 bg-zinc-800/50 rounded-lg border border-amber-700/50">
      {error && <div className="mb-3 p-2 bg-red-900/30 text-red-300 text-xs rounded border border-red-800/50">{error}</div>}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm text-white">{source.id}</span>
        <span className="text-xs text-amber-400">Editing</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="col-span-2">
          <label className="block text-xs text-zinc-500 mb-1">Git URL</label>
          <input
            type="text"
            value={formData.git_url}
            onChange={(e) => setFormData({ ...formData, git_url: e.target.value })}
            className="w-full px-2 py-1.5 text-xs bg-zinc-900/80 border border-zinc-700/50 rounded text-white"
          />
        </div>
        <div>
          <label className="block text-xs text-zinc-500 mb-1">Branch</label>
          <input
            type="text"
            value={formData.branch}
            onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
            className="w-full px-2 py-1.5 text-xs bg-zinc-900/80 border border-zinc-700/50 rounded text-white"
          />
        </div>
        <div>
          <label className="block text-xs text-zinc-500 mb-1">Path</label>
          <input
            type="text"
            value={formData.path}
            onChange={(e) => setFormData({ ...formData, path: e.target.value })}
            className="w-full px-2 py-1.5 text-xs bg-zinc-900/80 border border-zinc-700/50 rounded text-white"
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
        <div className="flex items-end gap-2">
          <button
            type="submit"
            className="flex-1 px-3 py-1.5 text-xs bg-amber-800/60 hover:bg-amber-700/60 text-amber-200 rounded transition border border-amber-700/50"
          >
            Save
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 text-xs bg-zinc-700/50 hover:bg-zinc-600/50 text-zinc-300 rounded transition border border-zinc-600/50"
          >
            Cancel
          </button>
        </div>
      </div>
    </form>
  )
}

function SourceItem({ source, sourceTypeLabels, onEdit, onToggle, onDelete }) {
  return (
    <div
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
          onClick={onEdit}
          className="px-2 py-1 text-xs bg-amber-900/30 text-amber-300/80 border border-amber-800/30 hover:bg-amber-800/40 rounded transition"
        >
          Edit
        </button>
        <button
          onClick={onToggle}
          className={`px-2 py-1 text-xs rounded transition border ${
            source.enabled
              ? 'bg-emerald-900/30 text-emerald-300/80 border-emerald-800/30 hover:bg-emerald-800/40'
              : 'bg-zinc-800/50 text-zinc-500 border-zinc-700/30 hover:bg-zinc-700/50'
          }`}
        >
          {source.enabled ? 'Enabled' : 'Disabled'}
        </button>
        <button
          onClick={onDelete}
          className="px-2 py-1 text-xs bg-red-900/30 text-red-300/80 border border-red-800/30 hover:bg-red-800/40 rounded transition"
        >
          Delete
        </button>
      </div>
    </div>
  )
}
