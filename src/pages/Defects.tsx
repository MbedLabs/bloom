import { useMemo, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { defectsApi, Defect, extractApiErrorMessage } from '../api/client'
import { ArrowUpDown, ChevronDown, ChevronUp, Plus, Bug, ExternalLink, Search } from 'lucide-react'
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

const STATUS_OPTIONS = ['Open', 'Triaged', 'In Progress', 'Resolved', 'Verified', 'Closed', 'Rejected', 'Duplicate']
const SEVERITY_OPTIONS = ['Critical', 'High', 'Medium', 'Low']

type SortField = 'updated_at' | 'defect_id' | 'title' | 'status' | 'severity'
type SortDir = 'asc' | 'desc'

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
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState<SortField>('updated_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
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
    queryFn: () =>
      defectsApi.list(projectId, {
        ...(filterStatus ? { status: filterStatus } : {}),
        ...(filterSeverity ? { severity: filterSeverity } : {}),
      }),
    enabled: !!projectId,
  })

  const sortedFiltered = useMemo(() => {
    let list = defects ?? []
    const q = search.trim().toLowerCase()
    if (q) {
      list = list.filter(
        (d) =>
          d.defect_id.toLowerCase().includes(q) ||
          d.title.toLowerCase().includes(q) ||
          d.status.toLowerCase().includes(q)
      )
    }
    const mult = sortDir === 'asc' ? 1 : -1
    return [...list].sort((a, b) => {
      if (sortField === 'updated_at') {
        return mult * (new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime())
      }
      if (sortField === 'defect_id') {
        return mult * a.defect_id.localeCompare(b.defect_id)
      }
      if (sortField === 'title') {
        return mult * a.title.localeCompare(b.title)
      }
      if (sortField === 'status') {
        return mult * a.status.localeCompare(b.status)
      }
      return mult * a.severity.localeCompare(b.severity)
    })
  }, [defects, search, sortField, sortDir])

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir(field === 'updated_at' ? 'desc' : 'asc')
    }
  }

  const createMutation = useMutation({
    mutationFn: defectsApi.create,
    onMutate: () => setCreateError(''),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['defects', projectId] })
      setShowCreate(false)
      setForm({
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
    },
    onError: (err) => setCreateError(extractApiErrorMessage(err)),
  })

  const canEdit = user?.role === 'admin' || user?.role === 'maintainer'

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      project_id: projectId,
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

  const SortHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <th
      className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase cursor-pointer select-none hover:text-foreground transition-colors"
      onClick={() => toggleSort(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        {sortField === field ? (
          sortDir === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-30" />
        )}
      </div>
    </th>
  )

  if (!project) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading project...</div>
  }

  const totalFromApi = defects?.length ?? 0
  const shown = sortedFiltered.length

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Link to={`/projects/${prefix}`} className="hover:text-primary transition-colors">
              {project.name}
            </Link>
            <span>/</span>
            <span className="text-foreground">Defects</span>
          </div>
          <h2 className="text-xl font-bold text-foreground">Defects</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {shown} of {totalFromApi} defect{totalFromApi !== 1 ? 's' : ''} shown
            {search.trim() ? ' (filtered)' : ''}
          </p>
        </div>
        {canEdit && (
          <button
            type="button"
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-all"
          >
            <Plus className="h-4 w-4" />
            New Defect
          </button>
        )}
      </div>

      <section className="rounded-lg border border-border bg-card">
        <div className="grid grid-cols-1 gap-3 border-b border-border p-4 lg:grid-cols-[minmax(260px,1fr)_auto_auto_auto]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search ID, title, status..."
              title="Filter defects in the current list"
              className="w-full rounded-md border border-input bg-background py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring"
            />
          </div>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            title="Filter by status"
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            title="Filter by severity"
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">All severities</option>
            {SEVERITY_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </section>

      {showCreate && (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">Create defect</h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Defect ID</label>
                <input
                  required
                  value={form.defect_id}
                  onChange={(e) => setForm({ ...form, defect_id: e.target.value })}
                  placeholder={`${prefix}-DEF-001`}
                  title="Defect ID"
                  className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Title</label>
                <input
                  required
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  title="Title"
                  className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3}
                title="Description"
                className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Severity</label>
                <select
                  value={form.severity}
                  onChange={(e) => setForm({ ...form, severity: e.target.value })}
                  title="Severity"
                  className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                >
                  {SEVERITY_OPTIONS.map((s) => (
                    <option key={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Priority</label>
                <select
                  value={form.priority}
                  onChange={(e) => setForm({ ...form, priority: e.target.value })}
                  title="Priority"
                  className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                >
                  {['Low', 'Medium', 'High', 'Critical'].map((s) => (
                    <option key={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="border-t border-border pt-4 mt-4">
              <h4 className="text-sm font-semibold text-foreground mb-3">External issue (optional)</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Tracker</label>
                  <select
                    value={form.external_tracker}
                    onChange={(e) => setForm({ ...form, external_tracker: e.target.value })}
                    title="External tracker"
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                  >
                    <option value="">None</option>
                    <option value="github">GitHub</option>
                    <option value="gitlab">GitLab</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Repository</label>
                  <input
                    value={form.external_repo_full_name}
                    onChange={(e) => setForm({ ...form, external_repo_full_name: e.target.value })}
                    placeholder="owner/repo"
                    title="Repository"
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Issue number</label>
                  <input
                    type="number"
                    value={form.external_issue_number}
                    onChange={(e) => setForm({ ...form, external_issue_number: e.target.value })}
                    placeholder="42"
                    title="Issue number"
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Issue URL</label>
                  <input
                    value={form.external_issue_url}
                    onChange={(e) => setForm({ ...form, external_issue_url: e.target.value })}
                    placeholder="https://github.com/..."
                    title="Issue URL"
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                  />
                </div>
              </div>
            </div>

            {createError && <p className="text-sm text-destructive">{createError}</p>}
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 border border-input rounded-md text-sm">
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm disabled:opacity-50"
              >
                {createMutation.isPending ? 'Creating...' : 'Create defect'}
              </button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-8 text-center text-muted-foreground">Loading defects...</div>
      ) : !defects || defects.length === 0 ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-16 text-center">
          <Bug className="h-12 w-12 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-muted-foreground">No defects yet.</p>
        </div>
      ) : sortedFiltered.length === 0 ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-8 text-center text-muted-foreground">
          No defects match your search.
        </div>
      ) : (
        <div className="bg-card rounded-lg border border-border shadow-elegant overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[800px]">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <SortHeader field="defect_id">ID</SortHeader>
                  <SortHeader field="title">Title</SortHeader>
                  <SortHeader field="status">Status</SortHeader>
                  <SortHeader field="severity">Severity</SortHeader>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Priority</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">External</th>
                  <SortHeader field="updated_at">Updated</SortHeader>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {sortedFiltered.map((defect: Defect) => (
                  <tr
                    key={defect.id}
                    onClick={() => navigate(`/projects/${prefix}/defects/${defect.id}`)}
                    className="hover:bg-accent/40 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 font-mono text-xs text-primary whitespace-nowrap">{defect.defect_id}</td>
                    <td className="px-6 py-4 text-foreground font-medium truncate max-w-[320px]">{defect.title}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[defect.status] || 'bg-gray-100 text-gray-600'}`}
                      >
                        {defect.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_COLORS[defect.severity] || 'bg-gray-100 text-gray-600'}`}
                      >
                        {defect.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-muted-foreground text-xs">{defect.priority}</td>
                    <td className="px-6 py-4">
                      {defect.external_issue_url ? (
                        <a
                          href={defect.external_issue_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-primary hover:text-primary/80 text-xs"
                        >
                          <ExternalLink className="h-3 w-3" />#{defect.external_issue_number}
                        </a>
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-muted-foreground text-xs whitespace-nowrap">{formatDateTime(defect.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
