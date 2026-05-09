import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { campaignsApi, TestCampaignItem } from '../api/client'
import { ArrowLeft, Clock, MessageSquare, Pencil, Trash2, FlaskConical, X } from 'lucide-react'
import { DocumentLinksPanel } from '../components/DocumentLinksPanel'
import { docUrl } from '../types/doc'

const CAMPAIGN_STATUSES = ['Planned', 'Scope', 'In Progress', 'Completed', 'Aborted']

type ScopeFilter = 'all' | 'ad_hoc' | number

export default function CampaignDetail() {
  const { prefix, campaignId } = useParams<{ prefix: string; campaignId: string }>()
  const campId = parseInt(campaignId || '0')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [editOpen, setEditOpen] = useState(false)
  const [editForm, setEditForm] = useState({ name: '', description: '', status: '' })
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>('all')

  const editNameRef = useRef<HTMLInputElement>(null)

  const { data: campaign, isLoading } = useQuery({
    queryKey: ['campaign', campId],
    queryFn: () => campaignsApi.get(campId),
    enabled: !!campId,
  })

  const updateMutation = useMutation({
    mutationFn: (data: { name?: string; description?: string; status?: string }) =>
      campaignsApi.update(campId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', campId] })
      setEditOpen(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => campaignsApi.delete(campId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
      navigate(`/projects/${prefix}/campaigns`)
    },
  })

  useEffect(() => {
    if (editOpen) editNameRef.current?.focus()
  }, [editOpen])

  const openEdit = () => {
    if (!campaign) return
    setEditForm({ name: campaign.name, description: campaign.description || '', status: campaign.status })
    setEditOpen(true)
  }

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate({
      name: editForm.name,
      description: editForm.description || undefined,
      status: editForm.status,
    })
  }

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') setEditOpen(false)
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!campaign) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Campaign Not Found</h3>
        <Link to={`/projects/${prefix}/campaigns`} className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Campaigns
        </Link>
      </div>
    )
  }

  const total = campaign.total_items
  const suiteScopes = campaign.suite_scopes ?? []
  const adHocItems = campaign.ad_hoc_items ?? []

  const filteredItems: TestCampaignItem[] = (() => {
    if (scopeFilter === 'all') return campaign.items ?? []
    if (scopeFilter === 'ad_hoc') return adHocItems
    const scope = suiteScopes.find((s) => s.suite.id === scopeFilter)
    return scope?.items ?? []
  })()

  const filterLabel = (() => {
    if (scopeFilter === 'all') return 'All test cases (union)'
    if (scopeFilter === 'ad_hoc') return 'Other / ad-hoc'
    const scope = suiteScopes.find((s) => s.suite.id === scopeFilter)
    return scope?.suite.name ?? 'Unknown suite'
  })()

  return (
    <div className="animate-fade-in space-y-6">
      {/* Hero row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${prefix}/campaigns`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <div className="flex items-center space-x-3">
              <h2 className="text-2xl font-bold text-foreground">{campaign.name}</h2>
              <CampaignStatusBadge status={campaign.status} />
            </div>
            {campaign.description && <p className="text-muted-foreground mt-0.5">{campaign.description}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={openEdit} className="inline-flex items-center px-3 py-1.5 border border-input text-foreground rounded-md hover:bg-accent/50 text-sm">
            <Pencil className="h-3.5 w-3.5 mr-1.5" /> Edit
          </button>
          <button onClick={() => setConfirmDelete(true)} className="inline-flex items-center px-3 py-1.5 border border-destructive/30 text-destructive rounded-md hover:bg-destructive/10 text-sm">
            <Trash2 className="h-3.5 w-3.5 mr-1.5" /> Delete
          </button>
        </div>
      </div>

      {/* Edit modal */}
      {editOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onKeyDown={handleEditKeyDown}>
          <div className="bg-card rounded-lg shadow-elegant p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-foreground">Edit campaign</h3>
              <button onClick={() => setEditOpen(false)} aria-label="Close" className="p-1 hover:bg-accent/50 rounded-md text-muted-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div>
                <label htmlFor="edit-name" className="block text-sm font-medium text-foreground mb-1">Name</label>
                <input id="edit-name" ref={editNameRef} type="text" required value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label htmlFor="edit-desc" className="block text-sm font-medium text-foreground mb-1">Description</label>
                <textarea id="edit-desc" value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring" rows={2} />
              </div>
              <div>
                <label htmlFor="edit-status" className="block text-sm font-medium text-foreground mb-1">Status</label>
                <select id="edit-status" value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring">
                  {CAMPAIGN_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setEditOpen(false)} className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50 text-sm">Cancel</button>
                <button type="submit" disabled={updateMutation.isPending} className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 text-sm">{updateMutation.isPending ? 'Saving...' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-elegant p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold text-foreground mb-2">Delete Campaign?</h3>
            <p className="text-sm text-muted-foreground mb-4">This action cannot be undone. All campaign items will be removed.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDelete(false)} className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50 text-sm">Cancel</button>
              <button onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending} className="px-4 py-2 bg-destructive text-white rounded-md hover:bg-destructive/90 disabled:opacity-50 text-sm">{deleteMutation.isPending ? 'Deleting...' : 'Delete'}</button>
            </div>
          </div>
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard label="Suites" value={campaign.suites?.length ?? 0} color="text-primary" />
        <StatCard label="Test cases (resolved)" value={total} color="text-foreground" />
        <StatCard label="Bud Run" value={campaign.bud_run_id || '-'} color="text-foreground" />
        <StatCard label="Req Coverage" value={campaign.related_requirements?.length || 0} color="text-emerald-600" />
      </div>

      {/* Suites in this campaign — primary section, moved up */}
      <div className="bg-card rounded-lg shadow-elegant p-5">
        <h3 className="text-sm font-medium text-muted-foreground mb-3">Suites in this campaign</h3>
        {campaign.suites && campaign.suites.length > 0 ? (
          <div className="space-y-2">
            {campaign.suites.map((suite) => (
              <Link key={suite.id} to={`/projects/${prefix}/suites/${suite.id}`} className="flex items-center justify-between gap-4 p-3 rounded-md border border-border hover:bg-accent/30 transition-colors">
                <div>
                  <div className="font-mono text-sm text-primary">{suite.suite_id}</div>
                  <div className="text-foreground mt-0.5">{suite.name}</div>
                </div>
                <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{suite.status}</span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No suites linked to this campaign.</p>
        )}
      </div>

      {/* Bud Execution Link */}
      <div className="bg-card rounded-lg shadow-elegant p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-foreground">Bud Execution Link</span>
          {campaign.bud_run_status && <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{campaign.bud_run_status}</span>}
        </div>
        {campaign.bud_run_url ? (
          <a href={campaign.bud_run_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center px-3 py-2 rounded-md bg-primary text-white hover:bg-primary/90 text-sm">
            Open in Bud TMP
          </a>
        ) : (
          <div className="text-sm text-muted-foreground">NA</div>
        )}
      </div>

      {/* Configuration */}
      {campaign.configuration && (
        <div className="bg-card rounded-lg shadow-elegant p-5">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Configuration</h3>
          <div className="flex items-center space-x-4 text-sm">
            <span className="text-foreground font-medium">{campaign.configuration.name}</span>
            {campaign.configuration.environment && (
              <span className="px-2 py-0.5 bg-muted rounded text-xs text-muted-foreground">{campaign.configuration.environment}</span>
            )}
          </div>
        </div>
      )}

      {/* Requirement Coverage */}
      <div className="bg-card rounded-lg shadow-elegant p-5">
        <h3 className="text-sm font-medium text-muted-foreground mb-3">Requirement Coverage</h3>
        {campaign.related_requirements && campaign.related_requirements.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {campaign.related_requirements.map((req) => (
              <Link key={req.id} to={docUrl(prefix!, 'REQ', req.req_id)} className="inline-flex items-center px-3 py-2 rounded-md bg-primary/10 text-primary hover:bg-primary/15 text-sm">
                <span className="font-mono mr-2">{req.req_id}</span>
                {req.title}
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No requirements are covered by this campaign scope yet.</p>
        )}
      </div>

      {/* Related Concepts */}
      {campaign.related_concepts && campaign.related_concepts.length > 0 && (
        <div className="bg-card rounded-lg shadow-elegant p-5">
          <h3 className="text-sm font-medium text-muted-foreground mb-3">Related Concepts</h3>
          <div className="flex flex-wrap gap-2">
            {campaign.related_concepts.map((concept) => (
              <Link key={concept.id} to={docUrl(prefix!, 'TCO', concept.concept_id)} className="inline-flex items-center px-3 py-2 rounded-md bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 hover:bg-cyan-500/15 text-sm">
                <FlaskConical className="h-3.5 w-3.5 mr-1.5" />
                <span className="font-mono mr-2">{concept.concept_id}</span>
                {concept.name}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Linked documents (defects, requirements, specs, etc.) */}
      <DocumentLinksPanel
        projectId={campaign.project_id}
        projectPrefix={prefix || ''}
        sourceType="CMP"
        sourceId={campaign.id}
      />

      {/* Resolved test cases — with suite dropdown filter */}
      <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h3 className="text-lg font-semibold">Resolved test cases</h3>
            <p className="text-xs text-muted-foreground mt-0.5">Union of test cases from the suites above; used for Bud result sync.</p>
          </div>
          {(suiteScopes.length > 0 || adHocItems.length > 0) && (
            <div className="flex items-center gap-2">
              <label htmlFor="scope-filter" className="text-sm text-muted-foreground whitespace-nowrap">View suite:</label>
              <select
                id="scope-filter"
                value={String(scopeFilter)}
                onChange={(e) => {
                  const v = e.target.value
                  setScopeFilter(v === 'all' ? 'all' : v === 'ad_hoc' ? 'ad_hoc' : Number(v))
                }}
                className="px-3 py-1.5 bg-background border border-input rounded-md text-sm focus:ring-2 focus:ring-ring min-w-[180px]"
              >
                <option value="all">All test cases (union)</option>
                {suiteScopes.map((ss) => (
                  <option key={ss.suite.id} value={String(ss.suite.id)}>
                    {ss.suite.name} ({ss.items.length})
                  </option>
                ))}
                {adHocItems.length > 0 && (
                  <option value="ad_hoc">Other / ad-hoc ({adHocItems.length})</option>
                )}
              </select>
            </div>
          )}
        </div>

        {filteredItems.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            {scopeFilter === 'all'
              ? 'No test cases in this campaign scope.'
              : `No test cases for "${filterLabel}".`}
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filteredItems.map((item) => (
              <div key={item.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Clock className="h-5 w-5 text-primary/60" />
                    <div>
                      {item.test_case ? (
                        <Link to={docUrl(prefix!, 'TC', item.test_case.tc_id)} className="font-mono text-sm text-primary hover:text-primary/80 font-medium">
                          {item.test_case.tc_id}
                        </Link>
                      ) : (
                        <span className="text-sm text-muted-foreground">TC#{item.test_case_id}</span>
                      )}
                      {item.test_case && <span className="ml-2 text-foreground">{item.test_case.title}</span>}
                      {item.test_case?.linked_requirements && item.test_case.linked_requirements.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {item.test_case.linked_requirements.map((req) => (
                            <Link key={req.id} to={docUrl(prefix!, 'REQ', req.req_id)} className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary hover:bg-primary/15">
                              <span className="font-mono mr-1">{req.req_id}</span>
                              {req.title}
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <ResultBadge result={item.result || item.status || 'Pending'} />
                    {item.result && item.status && (
                      <span className="text-xs text-muted-foreground">{item.status}</span>
                    )}
                  </div>
                </div>

                {item.comment && (
                  <div className="mt-2 flex items-start space-x-2 text-sm">
                    <MessageSquare className="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                    <span className="text-muted-foreground">{item.comment}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div className="bg-card rounded-lg shadow-elegant p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

function CampaignStatusBadge({ status }: { status: string }) {
  const config: Record<string, { colors: string }> = {
    Planned: { colors: 'bg-gray-500/10 text-gray-700 dark:text-gray-400' },
    Scope: { colors: 'bg-blue-500/10 text-blue-700 dark:text-blue-400' },
    Completed: { colors: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' },
    Aborted: { colors: 'bg-red-500/10 text-red-700 dark:text-red-400' },
  }
  const cfg = config[status] || config.Planned
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cfg.colors}`}>{status}</span>
}

function ResultBadge({ result }: { result: string }) {
  const config: Record<string, string> = {
    Passed: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Failed: 'bg-red-500/10 text-red-700 dark:text-red-400',
    Skipped: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
    Planned: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Scope: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Pending: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Linked: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400',
    Executed: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${config[result] || config.Pending}`}>
      {result}
    </span>
  )
}
