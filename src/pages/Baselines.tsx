import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Layers, Plus, GitCompareArrows } from 'lucide-react'

import { baselinesApi, projectsApi } from '../api/client'
import { formatDateTime } from '../test/date-utils'

export default function Baselines() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [form, setForm] = useState({ project_id: '', name: '', description: '', baseline_type: 'Milestone' })

  const { data: baselines, isLoading } = useQuery({
    queryKey: ['baselines'],
    queryFn: () => baselinesApi.list(),
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  const createMutation = useMutation({
    mutationFn: baselinesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['baselines'] })
      setShowCreate(false)
      setForm({ project_id: '', name: '', description: '', baseline_type: 'Milestone' })
    },
  })

  const selectedBaseline = useMemo(
    () => baselines?.find((item) => item.id === selectedId) ?? baselines?.[0] ?? null,
    [baselines, selectedId]
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      project_id: Number(form.project_id),
      name: form.name,
      description: form.description || undefined,
      baseline_type: form.baseline_type,
    })
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Baselines</h2>
          <p className="text-muted-foreground">Snapshot and compare project artefacts at specific points in time</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90">
          <Plus className="h-4 w-4" />
          New Baseline
        </button>
      </div>

      {isLoading ? (
        <div className="bg-card rounded-lg shadow-elegant p-8 text-center text-muted-foreground">Loading...</div>
      ) : !baselines || baselines.length === 0 ? (
        <div className="bg-card rounded-lg shadow-elegant p-12 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-4">
            <Layers className="h-8 w-8 text-primary/40" />
          </div>
          <h3 className="text-lg font-medium text-foreground mb-2">No Baselines Yet</h3>
          <p className="text-muted-foreground max-w-md mx-auto">Create a baseline to freeze the current project state for audit, comparison, and release tracking.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6">
          <div className="bg-card rounded-lg border border-border shadow-elegant overflow-hidden">
            <div className="px-4 py-3 border-b border-border text-sm font-medium text-foreground">Available Baselines</div>
            <div className="divide-y divide-border max-h-[620px] overflow-y-auto">
              {baselines.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                  className={`w-full text-left p-4 transition-colors ${selectedBaseline?.id === item.id ? 'bg-primary/5' : 'hover:bg-accent/40'}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium text-foreground">{item.name}</div>
                      <div className="text-xs text-muted-foreground mt-1">Project #{item.project_id} · {item.baseline_type}</div>
                    </div>
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{item.status}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-card rounded-lg border border-border shadow-elegant p-6">
            {selectedBaseline && (
              <>
                <div className="flex items-start justify-between gap-4 mb-6">
                  <div>
                    <h3 className="text-xl font-semibold text-foreground">{selectedBaseline.name}</h3>
                    <p className="text-sm text-muted-foreground mt-1">{selectedBaseline.description || 'No description provided.'}</p>
                  </div>
                  <div className="text-right text-sm text-muted-foreground">
                    <div>{selectedBaseline.baseline_type}</div>
                    <div>{formatDateTime(selectedBaseline.created_at)}</div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {Object.entries((selectedBaseline.snapshot as Record<string, { count?: number; ids?: string[]; titles?: string[] }>) || {}).map(([key, value]) => (
                    <div key={key} className="rounded-lg border border-border p-4 bg-background/60">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-sm font-medium text-foreground capitalize">{key.replace('_', ' ')}</div>
                        <div className="text-lg font-bold text-foreground">{value?.count ?? 0}</div>
                      </div>
                      <div className="text-xs text-muted-foreground break-words">
                        {value?.ids?.slice(0, 6).join(', ') || value?.titles?.slice(0, 6).join(', ') || 'No items'}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-6 rounded-lg border border-border p-4 bg-background/60 flex items-center gap-3 text-sm text-muted-foreground">
                  <GitCompareArrows className="h-4 w-4" />
                  Compare this snapshot against the live project state by opening the project workspace and reviewing current counts side by side.
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-xl shadow-glow max-w-md w-full">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-foreground">Create Baseline</h3>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Project</label>
                <select value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md" required>
                  <option value="">Select project</option>
                  {(projects ?? []).map((project) => (
                    <option key={project.id} value={project.id}>{project.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Name</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Type</label>
                <select value={form.baseline_type} onChange={(e) => setForm({ ...form, baseline_type: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md">
                  <option>Milestone</option>
                  <option>Release</option>
                  <option>Audit</option>
                  <option>Review</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Description</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="w-full px-3 py-2 bg-background border border-input rounded-md" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 border border-border rounded-md text-sm text-muted-foreground hover:bg-accent">Cancel</button>
                <button type="submit" disabled={createMutation.isPending} className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50">
                  {createMutation.isPending ? 'Creating...' : 'Create Baseline'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
