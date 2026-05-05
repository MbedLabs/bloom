import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Edit2, Plus, SlidersHorizontal, Trash2, X } from 'lucide-react'

import { projectVariablesApi, ProjectVariable } from '../api/client'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'

export default function ProjectParameters() {
  const { prefix } = useParams<{ prefix: string }>()
  const { data: project, isLoading: projectLoading } = useProjectByPrefix(prefix)
  const projectId = project?.id || 0
  const queryClient = useQueryClient()

  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ kind: 'variable' as ProjectVariable['kind'], key: '', value: '', description: '' })
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState({ kind: 'variable' as ProjectVariable['kind'], key: '', value: '', description: '' })

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
      setCreateForm({ kind: 'variable', key: '', value: '', description: '' })
    },
  })

  useEffect(() => {
    if (!editingId || !variables) return
    const currentItem = variables.find((item) => item.id === editingId)
    if (!currentItem) return
    setEditForm({
      kind: currentItem.kind,
      key: currentItem.key,
      value: currentItem.value,
      description: currentItem.description || '',
    })
  }, [editingId, variables])

  const deleteMutation = useMutation({
    mutationFn: projectVariablesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectVariables', projectId] })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof projectVariablesApi.update>[1] }) =>
      projectVariablesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectVariables', projectId] })
      setEditingId(null)
    },
  })

  const onCreate = (e: React.FormEvent) => {
    e.preventDefault()
    const key = createForm.key.trim()
    const value = createForm.value.trim()
    if (!key || !value) return

    createMutation.mutate({
      project_id: projectId,
      kind: createForm.kind,
      key,
      value,
      description: createForm.description || null,
    })
  }

  const onEdit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingId) return

    const key = editForm.key.trim()
    const value = editForm.value.trim()
    if (!key || !value) return

    updateMutation.mutate({
      id: editingId,
      data: {
        kind: editForm.kind,
        key,
        value,
        description: editForm.description || null,
      },
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
              <label className="block text-sm font-medium text-foreground mb-1">Kind</label>
              <select
                value={createForm.kind}
                onChange={(e) => setCreateForm({ ...createForm, kind: e.target.value as ProjectVariable['kind'] })}
                title="Select item kind"
                className="w-full px-3 py-2 bg-background border border-input rounded-md"
              >
                <option value="variable">Variable</option>
                <option value="parameter">Parameter</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Key</label>
              <input
                required
                value={createForm.key}
                onChange={(e) => setCreateForm({ ...createForm, key: e.target.value })}
                title="Variable or parameter key"
                placeholder="Enter a key"
                className="w-full px-3 py-2 bg-background border border-input rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Value</label>
              <textarea
                required
                rows={3}
                value={createForm.value}
                onChange={(e) => setCreateForm({ ...createForm, value: e.target.value })}
                title="Variable or parameter value"
                placeholder="Enter a value"
                className="w-full px-3 py-2 bg-background border border-input rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Description</label>
              <textarea
                rows={2}
                value={createForm.description}
                onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                title="Optional description"
                placeholder="Optional description"
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
                  <Th>Kind</Th>
                  <Th>Key</Th>
                  <Th>Value</Th>
                  <Th>Description</Th>
                  <Th>Actions</Th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {variables.map((item: ProjectVariable) => (
                  editingId === item.id ? (
                    <tr key={item.id} className="bg-accent/30">
                      <Td>
                        <select
                          value={editForm.kind}
                          onChange={(e) => setEditForm({ ...editForm, kind: e.target.value as ProjectVariable['kind'] })}
                          title="Select item kind"
                          className="w-full min-w-28 px-2 py-1.5 bg-background border border-input rounded-md text-sm text-foreground"
                        >
                          <option value="variable">Variable</option>
                          <option value="parameter">Parameter</option>
                        </select>
                      </Td>
                      <Td>
                        <input
                          value={editForm.key}
                          onChange={(e) => setEditForm({ ...editForm, key: e.target.value })}
                          title="Variable or parameter key"
                          placeholder="Enter a key"
                          className="w-full min-w-40 px-2 py-1.5 bg-background border border-input rounded-md text-sm text-foreground font-mono"
                        />
                      </Td>
                      <Td>
                        <textarea
                          rows={2}
                          value={editForm.value}
                          onChange={(e) => setEditForm({ ...editForm, value: e.target.value })}
                          title="Variable or parameter value"
                          placeholder="Enter a value"
                          className="w-full min-w-64 px-2 py-1.5 bg-background border border-input rounded-md text-sm text-foreground font-mono"
                        />
                      </Td>
                      <Td>
                        <textarea
                          rows={2}
                          value={editForm.description}
                          onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                          title="Optional description"
                          placeholder="Optional description"
                          className="w-full min-w-48 px-2 py-1.5 bg-background border border-input rounded-md text-sm text-foreground"
                        />
                      </Td>
                      <Td>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={onEdit}
                            disabled={updateMutation.isPending}
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-primary text-white hover:bg-primary/90 disabled:opacity-50"
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-input text-foreground hover:bg-accent/50"
                          >
                            <X className="h-3.5 w-3.5" />
                            Cancel
                          </button>
                        </div>
                      </Td>
                    </tr>
                  ) : (
                    <tr key={item.id} className="hover:bg-accent/50">
                      <Td><span className="font-mono text-sm text-foreground">{item.kind}</span></Td>
                      <Td><span className="font-mono text-sm text-foreground">{item.key}</span></Td>
                      <Td><span className="font-mono text-xs text-muted-foreground">{item.value}</span></Td>
                      <Td>{item.description || '-'}</Td>
                      <Td>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setEditingId(item.id)}
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-input text-foreground hover:bg-accent/50"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                            Edit
                          </button>
                          <button
                            onClick={() => deleteMutation.mutate(item.id)}
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-red-500/50 text-red-600 hover:bg-red-500/10"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </button>
                        </div>
                      </Td>
                    </tr>
                  )
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
