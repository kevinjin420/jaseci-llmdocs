import { useState } from 'react'
import type { Variant } from '@/utils/types'
import { API_BASE } from '@/utils/types'

interface Props {
  variants: Variant[]
  onRefresh: () => void
}

export default function VariantsView({ variants, onRefresh }: Props) {
  const [isAddingVariant, setIsAddingVariant] = useState(false)
  const [formData, setFormData] = useState({ variant_name: '', url: '' })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      const response = await fetch(`${API_BASE}/variants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      if (response.ok) {
        setFormData({ variant_name: '', url: '' })
        setIsAddingVariant(false)
        onRefresh()
      } else {
        const error = await response.json()
        alert(`Error: ${error.error}`)
      }
    } catch (error) {
      alert('Failed to create variant')
      console.error(error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (variantName: string) => {
    if (deleteConfirm !== variantName) {
      setDeleteConfirm(variantName)
      return
    }

    try {
      const response = await fetch(`${API_BASE}/variants/${encodeURIComponent(variantName)}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        onRefresh()
        setDeleteConfirm(null)
      } else {
        const error = await response.json()
        alert(`Error: ${error.error}`)
      }
    } catch (error) {
      alert('Failed to delete variant')
      console.error(error)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold text-gray-200">Documentation Variants</h2>
          <p className="text-sm text-gray-400 mt-1">
            Manage documentation sources for benchmarking
          </p>
        </div>
        <button
          onClick={() => setIsAddingVariant(!isAddingVariant)}
          className="px-4 py-2 bg-terminal-accent text-black rounded hover:bg-opacity-80 transition-all font-medium cursor-pointer"
        >
          {isAddingVariant ? 'Cancel' : 'Add Variant'}
        </button>
      </div>

      {isAddingVariant && (
        <div className="bg-terminal-surface border border-terminal-border rounded p-6">
          <h3 className="text-lg font-semibold text-gray-200 mb-4">Add New Variant</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
              <input
                type="text"
                required
                value={formData.variant_name}
                onChange={(e) => setFormData({ ...formData, variant_name: e.target.value })}
                className="w-full px-3 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm focus:outline-none focus:border-terminal-accent"
                placeholder="e.g., jaseci-docs-v1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">URL</label>
              <input
                type="url"
                required
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                className="w-full px-3 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm focus:outline-none focus:border-terminal-accent"
                placeholder="https://example.com/docs.md"
              />
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-2 bg-terminal-accent text-black rounded hover:bg-opacity-80 transition-all font-medium disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isSubmitting ? 'Creating...' : 'Create Variant'}
              </button>
              <button
                type="button"
                onClick={() => setIsAddingVariant(false)}
                className="px-4 py-2 bg-zinc-700 text-gray-300 rounded hover:bg-zinc-600 transition-all cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-terminal-surface border border-terminal-border rounded">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-zinc-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">URL</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Size</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-terminal-border">
              {variants.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                    No variants found. Add your first variant to get started.
                  </td>
                </tr>
              ) : (
                variants.map((variant) => (
                  <tr key={variant.name} className="hover:bg-zinc-800/50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-300">{variant.name}</td>
                    <td className="px-6 py-4 text-sm text-gray-400 max-w-md truncate">
                      <a href={variant.url} target="_blank" rel="noopener noreferrer" className="hover:text-terminal-accent transition-colors">
                        {variant.url}
                      </a>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">{variant.size_kb} KB</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <button
                        onClick={() => handleDelete(variant.name)}
                        className={`px-3 py-1 rounded transition-all cursor-pointer ${
                          deleteConfirm === variant.name
                            ? 'bg-red-600 text-white hover:bg-red-700'
                            : 'bg-red-600/10 text-red-400 hover:bg-red-600/20'
                        }`}
                      >
                        {deleteConfirm === variant.name ? 'Confirm Delete' : 'Delete'}
                      </button>
                      {deleteConfirm === variant.name && (
                        <button
                          onClick={() => setDeleteConfirm(null)}
                          className="ml-2 px-3 py-1 bg-zinc-700 text-gray-300 rounded hover:bg-zinc-600 transition-all cursor-pointer"
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
