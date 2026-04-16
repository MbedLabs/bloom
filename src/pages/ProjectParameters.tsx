import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Plus, SlidersHorizontal, Trash2 } from 'lucide-react'

import { projectVariablesApi, ProjectVariable } from '../api/client'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'

export default function ProjectParameters() {
  const { prefix } = useParams<{ prefix: string }>()
  const { data: project, isLoading: projectLoading } = useProjectByPrefix(prefix)
  const projectId = project?.id || 0
  const queryClient = useQueryClient()

  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ key: '', value: '', description: '' })

  const { data: variables, isLoading: variablesLoading } = useQuery({
    queryKey: ['projectVariables', projectId],
    queryFn: () => projectVariablesApi.list(projectId),
    enabled: !!projectId,
  })

  const createMutation = useMutation({
    mutationFn: projectVariablesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectVariables', projectId] })
      setShowCreate(false)
      setForm({ key: '', value: '', description: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: projectVariablesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectVariables', projectId] })
    },
  })

  const onCreate = (e: React.FormEvent) => {
    e.preventDefault()
    const key = form.key.trim()
    const value = form.value.trim()
    if (!key || !value) return

    createMutation.mutate({
      project_id: projectId,
      kind: 'variable',
      key,
      value,
      description: form.description || null,
    })
  }

  if (projectLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!project) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Project Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Projects
        </Link>
      </div>
    )
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to={`/projects/${prefix}`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Project Parameters</h2>
            <p className="text-muted-foreground">{project.name}</p>
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Item
        </button>
      </div>

      {showCreate && (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-5">
          <h3 className="font-semibold text-foreground mb-4">New Parameter / Variable</h3>
          <form onSubmit={onCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Key</label>
              <input
                required
                value={form.key}
                onChange={(e) => setForm({ ...form, key: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-input rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Value</label>
              <textarea
                required
                rows={3}
                value={form.value}
                onChange={(e) => setForm({ ...form, value: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-input rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Description</label>
              <textarea
                rows={2}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-input rounded-md"
              />
            </div>
            <div className="pt-2 flex justify-end gap-3">
              <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50">Cancel</button>
              <button type="submit" disabled={createMutation.isPending} className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50">{createMutation.isPending ? 'Saving...' : 'Save'}</button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-card rounded-lg border border-border shadow-elegant p-5">
        <div className="flex items-center gap-2 mb-3">
          <SlidersHorizontal className="h-4 w-4 text-primary" />
          <h3 className="font-semibold text-foreground">Parameters & Variables</h3>
        </div>
        {variablesLoading ? (
          <div className="text-sm text-muted-foreground">Loading...</div>
        ) : !variables || variables.length === 0 ? (
          <div className="text-sm text-muted-foreground">No items yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <Th>Key</Th>
                  <Th>Value</Th>
                  <Th>Description</Th>
                  <Th>Actions</Th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {variables.map((item: ProjectVariable) => (
                  <tr key={item.id} className="hover:bg-accent/50">
                    <Td><span className="font-mono text-sm text-foreground">{item.key}</span></Td>
                    <Td><span className="font-mono text-xs text-muted-foreground">{item.value}</span></Td>
                    <Td>{item.description || '-'}</Td>
                    <Td>
                      <button
                        onClick={() => deleteMutation.mutate(item.id)}
                        className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-red-500/50 text-red-600 hover:bg-red-500/10"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">{children}</th>
}

function Td({ children }: { children: React.ReactNode }) {
  return <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{children}</td>
}
