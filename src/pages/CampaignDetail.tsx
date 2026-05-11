import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { campaignsApi, type ArtefactLink, type TestCampaignItem } from '../api/client'
import { ArrowLeft, ChevronDown, ChevronRight, ExternalLink, Pencil, Trash2, X } from 'lucide-react'
import { DocumentLinksPanel } from '../components/DocumentLinksPanel'
import { usePageMeta } from '../contexts/PageMetaContext'
import { docUrl } from '../types/doc'
import { docRegistryListUrl } from '../lib/docRegistryParams'

const CAMPAIGN_STATUSES = ['Planned', 'Scope', 'In Progress', 'Completed', 'Aborted']

export default function CampaignDetail({ resolvedId }: { resolvedId?: number } = {}) {
  const { prefix, campaignId } = useParams<{ prefix: string; campaignId: string }>()
  const campId = resolvedId || parseInt(campaignId || '0')
  const navigate = useNavigate()
  const location = useLocation()
  const backUrl = (location.state as { returnTo?: string } | null)?.returnTo
    || docRegistryListUrl(prefix!, 'CMP')
  const queryClient = useQueryClient()

  const [editOpen, setEditOpen] = useState(false)
  const [editForm, setEditForm] = useState({ name: '', description: '', status: '' })
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [expandedSuites, setExpandedSuites] = useState<Set<number>>(new Set())
  const [adHocExpanded, setAdHocExpanded] = useState(false)
  const { setCrumbLabel } = usePageMeta()

  const editNameRef = useRef<HTMLInputElement>(null)

  const { data: campaign, isLoading } = useQuery({
    queryKey: ['campaign', campId],
    queryFn: () => campaignsApi.get(campId),
    enabled: !!campId,
  })

  const { data: scopeLinks } = useQuery<ArtefactLink[]>({
    queryKey: ['campaign-scope-links', campId],
    queryFn: () => campaignsApi.scopeLinks(campId),
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
      navigate(docRegistryListUrl(prefix!, 'CMP'))
    },
  })

  useEffect(() => {
    if (campaign?.name) setCrumbLabel(campaign.name)
    return () => setCrumbLabel(undefined)
  }, [campaign?.name, setCrumbLabel])

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

  const toggleSuite = (suiteId: number) => {
    setExpandedSuites((prev) => {
      const next = new Set(prev)
      if (next.has(suiteId)) next.delete(suiteId)
      else next.add(suiteId)
      return next
    })
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!campaign) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Campaign Not Found</h3>
        <Link to={backUrl} className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Campaigns
        </Link>
      </div>
    )
  }

  const suiteScopes = campaign.suite_scopes ?? []
  const adHocItems = campaign.ad_hoc_items ?? []

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={backUrl} className="p-2 hover:bg-accent/50 rounded-md">
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Suites" value={suiteScopes.length} color="text-primary" />
        <StatCard label="Bud Run" value={campaign.bud_run_id || '-'} color="text-foreground" />
        <StatCard label="Status" value={campaign.status} color="text-foreground" />
      </div>

      {/* Suites — expandable inline list */}
      {(suiteScopes.length > 0 || adHocItems.length > 0) && (
        <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
          <div className="px-6 py-4 border-b border-border">
            <h3 className="text-lg font-semibold text-foreground">Suites</h3>
          </div>

          {suiteScopes.length === 0 && adHocItems.length > 0 ? (
            <div className="px-6 py-4 text-sm text-muted-foreground">No suites linked to this campaign.</div>
          ) : (
            <div className="divide-y divide-border">
              {suiteScopes.map((scope) => {
                const isOpen = expandedSuites.has(scope.suite.id)
                return (
                  <div key={scope.suite.id}>
                    <button
                      type="button"
                      onClick={() => toggleSuite(scope.suite.id)}
                      className="w-full px-6 py-4 flex items-center justify-between gap-4 hover:bg-accent/30 transition-colors text-left"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        {isOpen ? <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" /> : <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />}
                        <span className="font-mono text-xs text-primary shrink-0">{scope.suite.suite_id}</span>
                        <span className="text-foreground font-medium truncate">{scope.suite.name}</span>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className="text-xs text-muted-foreground">{scope.items.length} TC{scope.items.length !== 1 ? 's' : ''}</span>
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground">{scope.suite.status}</span>
                        <Link
                          to={`/projects/${prefix}/docs/test-suites/${scope.suite.suite_id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="p-1 rounded hover:bg-accent/50 text-muted-foreground hover:text-primary"
                          title="Open suite detail"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </Link>
                      </div>
                    </button>

                    {isOpen && (
                      <div className="border-t border-border bg-muted/20">
                        {scope.items.length === 0 ? (
                          <div className="px-10 py-4 text-sm text-muted-foreground">No test cases resolved for this suite yet.</div>
                        ) : (
                          <div className="divide-y divide-border/50">
                            {scope.items.map((item) => (
                              <CampaignItemRow key={item.id} item={item} prefix={prefix!} />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {adHocItems.length > 0 && (
            <div className="border-t border-border">
              <button
                type="button"
                onClick={() => setAdHocExpanded(!adHocExpanded)}
                className="w-full px-6 py-4 flex items-center justify-between gap-4 hover:bg-accent/30 transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  {adHocExpanded ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                  <span className="text-foreground font-medium">Other items</span>
                </div>
                <span className="text-xs text-muted-foreground">{adHocItems.length} TC{adHocItems.length !== 1 ? 's' : ''}</span>
              </button>
              {adHocExpanded && (
                <div className="border-t border-border bg-muted/20 divide-y divide-border/50">
                  {adHocItems.map((item) => (
                    <CampaignItemRow key={item.id} item={item} prefix={prefix!} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

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

      {/* Linked documents */}
      <DocumentLinksPanel
        projectId={campaign.project_id}
        projectPrefix={prefix || ''}
        sourceType="CMP"
        sourceId={campaign.id}
        derivedLinks={scopeLinks}
      />
    </div>
  )
}

function CampaignItemRow({ item, prefix }: { item: TestCampaignItem; prefix: string }) {
  return (
    <div className="px-10 py-3 flex items-center justify-between gap-4">
      <div className="min-w-0">
        {item.test_case ? (
          <div className="flex items-center gap-2">
            <Link to={docUrl(prefix, 'TC', item.test_case.tc_id)} className="font-mono text-xs text-primary hover:text-primary/80">
              {item.test_case.tc_id}
            </Link>
            <span className="text-sm text-foreground truncate">{item.test_case.title}</span>
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">TC#{item.test_case_id}</span>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <ResultBadge result={item.result || item.status || 'Pending'} />
        {item.result && item.status && item.result !== item.status && (
          <span className="text-xs text-muted-foreground">{item.status}</span>
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
