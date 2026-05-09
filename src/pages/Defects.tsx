import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { defectsApi, Defect, extractApiErrorMessage } from '../api/client'
import { ArrowLeft, Plus, Bug, ExternalLink } from 'lucide-react'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'
import { useAuth } from '../contexts/AuthContext'
import { formatDateTime } from '../test/date-utils'

const SEVERITY_COLORS: Record<string, string> = {
  Critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  High: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  Medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  Low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
}

const STATUS_COLORS: Record<string, string> = {
  Open: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  Triaged: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  'In Progress': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  Resolved: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400',
  Verified: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  Closed: 'bg-slate-100 text-slate-600 dark:bg-slate-800/30 dark:text-slate-400',
  Rejected: 'bg-gray-100 text-gray-600 dark:bg-gray-800/30 dark:text-gray-400',
  Duplicate: 'bg-gray-100 text-gray-600 dark:bg-gray-800/30 dark:text-gray-400',
}

export default function Defects() {
  const { prefix } = useParams<{ prefix: string }>()
  const { data: project } = useProjectByPrefix(prefix)
  const projectId = project?.id || 0
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const [showCreate, setShowCreate] = useState(false)
  const [createError, setCreateError] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterSeverity, setFilterSeverity] = useState('')
  const [form, setForm] = useState({
    defect_id: '',
    title: '',
    description: '',
    severity: 'Medium',
    priority: 'Medium',
    external_tracker: '',
    external_repo_full_name: '',
    external_issue_number: '',
    external_issue_url: '',
  })

  const { data: defects, isLoading } = useQuery({
    queryKey: ['defects', projectId, filterStatus, filterSeverity],
    queryFn: () => defectsApi.list(projectId, {
      ...(filterStatus ? { status: filterStatus } : {}),
      ...(filterSeverity ? { severity: filterSeverity } : {}),
    }),
    enabled: !!projectId,
  })

  const createMutation = useMutation({
    mutationFn: defectsApi.create,
    onMutate: () => setCreateError(''),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['defects', projectId] })
      setShowCreate(false)
      setForm({ defect_id: '', title: '', description: '', severity: 'Medium', priority: 'Medium', external_tracker: '', external_repo_full_name: '', external_issue_number: '', external_issue_url: '' })
    },
    onError: (err) => setCreateError(extractApiErrorMessage(err)),
  })

  const canEdit = user?.role === 'admin' || user?.role === 'maintainer'

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      project_id: projectId,
      defect_id: form.defect_id,
      title: form.title,
      description: form.description || null,
      severity: form.severity,
      priority: form.priority,
      external_tracker: form.external_tracker || null,
      external_repo_full_name: form.external_repo_full_name || null,
      external_issue_number: form.external_issue_number ? Number(form.external_issue_number) : null,
      external_issue_url: form.external_issue_url || null,
    })
  }

  if (!project) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading project...</div>

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to={`/projects/${prefix}`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <Bug className="h-6 w-6 text-rose-500" /> Defects
            </h1>
            <p className="text-sm text-muted-foreground">{project.name}</p>
          </div>
        </div>
        {canEdit && (
          <button onClick={() => setShowCreate(true)} className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 text-sm">
            <Plus className="h-4 w-4 mr-2" /> New Defect
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="px-3 py-2 bg-background border border-input rounded-md text-sm">
          <option value="">All Statuses</option>
          {['Open', 'Triaged', 'In Progress', 'Resolved', 'Verified', 'Closed', 'Rejected', 'Duplicate'].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)} className="px-3 py-2 bg-background border border-input rounded-md text-sm">
          <option value="">All Severities</option>
          {['Critical', 'High', 'Medium', 'Low'].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="bg-card rounded-lg shadow-elegant border border-border p-6">
          <h2 className="text-lg font-semibold text-foreground mb-4">Create Defect</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Defect ID</label>
                <input required value={form.defect_id} onChange={(e) => setForm({ ...form, defect_id: e.target.value })} placeholder={`${prefix}-DEF-001`} className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Title</label>
                <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Description</label>
              <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Severity</label>
                <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm">
                  {['Low', 'Medium', 'High', 'Critical'].map((s) => <option key={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Priority</label>
                <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm">
                  {['Low', 'Medium', 'High', 'Critical'].map((s) => <option key={s}>{s}</option>)}
                </select>
              </div>
            </div>

            {/* External issue fields */}
            <div className="border-t border-border pt-4 mt-4">
              <h3 className="text-sm font-semibold text-foreground mb-3">External Issue (optional)</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Tracker</label>
                  <select value={form.external_tracker} onChange={(e) => setForm({ ...form, external_tracker: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm">
                    <option value="">None</option>
                    <option value="github">GitHub</option>
                    <option value="gitlab">GitLab</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Repository</label>
                  <input value={form.external_repo_full_name} onChange={(e) => setForm({ ...form, external_repo_full_name: e.target.value })} placeholder="owner/repo" className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Issue Number</label>
                  <input type="number" value={form.external_issue_number} onChange={(e) => setForm({ ...form, external_issue_number: e.target.value })} placeholder="42" className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Issue URL</label>
                  <input value={form.external_issue_url} onChange={(e) => setForm({ ...form, external_issue_url: e.target.value })} placeholder="https://github.com/..." className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm" />
                </div>
              </div>
            </div>

            {createError && <p className="text-sm text-destructive">{createError}</p>}
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 border border-input rounded-md text-sm">Cancel</button>
              <button type="submit" disabled={createMutation.isPending} className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 text-sm disabled:opacity-50">
                {createMutation.isPending ? 'Creating...' : 'Create Defect'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Defects table */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading defects...</div>
      ) : !defects || defects.length === 0 ? (
        <div className="text-center py-16 bg-card rounded-lg border border-border">
          <Bug className="h-12 w-12 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-muted-foreground">No defects found.</p>
        </div>
      ) : (
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">ID</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Title</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Severity</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Priority</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">External</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Updated</th>
              </tr>
            </thead>
            <tbody>
              {defects.map((defect: Defect) => (
                <tr
                  key={defect.id}
                  onClick={() => navigate(`/projects/${prefix}/defects/${defect.id}`)}
                  className="border-b border-border last:border-0 hover:bg-accent/40 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-xs text-primary whitespace-nowrap">{defect.defect_id}</td>
                  <td className="px-4 py-3 text-foreground font-medium truncate max-w-[300px]">{defect.title}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[defect.status] || 'bg-gray-100 text-gray-600'}`}>
                      {defect.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_COLORS[defect.severity] || 'bg-gray-100 text-gray-600'}`}>
                      {defect.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{defect.priority}</td>
                  <td className="px-4 py-3">
                    {defect.external_issue_url ? (
                      <a href={defect.external_issue_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="inline-flex items-center gap-1 text-primary hover:text-primary/80 text-xs">
                        <ExternalLink className="h-3 w-3" />
                        #{defect.external_issue_number}
                      </a>
                    ) : (
                      <span className="text-muted-foreground text-xs">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs whitespace-nowrap">{formatDateTime(defect.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
