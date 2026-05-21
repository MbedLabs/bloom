import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUpDown, ExternalLink, GitBranch, History, MessageSquare, Pencil, RefreshCw, Trash2 } from 'lucide-react'
import { formatDateTime } from '../test/date-utils'
import { docUrl, docEditUrl, type DocType } from '../types/doc'
import { docRegistryListUrl } from '../lib/docRegistryParams'
import { DocEditor } from '../components/editor'
import DocDetailShell, { MetaItem, SectionCard, StatusBadge } from '../components/DocDetailShell'
import { DocumentLinksPanel } from '../components/DocumentLinksPanel'
import { useAuth } from '../contexts/AuthContext'

import {
  artefactsApi,
  ChangeRequest,
  changesApi,
  Defect,
  defectsApi,
  DesignItem,
  designsApi,
  extractApiErrorMessage,
  integrationsApi,
  RiskItem,
  risksApi,
  SyncEvent,
  TestConcept,
  testConceptsApi,
  projectsApi,
} from '../api/client'

type ArtefactKind = 'design' | 'risk' | 'change' | 'test-concept' | 'defect'
type ArtefactRecord = DesignItem | RiskItem | ChangeRequest | TestConcept | Defect
type DetailTab = 'overview' | 'comments' | 'activity' | 'related' | 'sync'

const SOURCE_TYPE_CODES: Record<ArtefactKind, string> = {
  design: 'DES',
  risk: 'RSK',
  change: 'CHG',
  'test-concept': 'CPT',
  defect: 'DEF',
}

const configs = {
  design: {
    singular: 'Design',
    docType: 'DES' as DocType,
    queryKey: 'design',
    listKey: 'designs',
    idField: 'design_id',
    titleField: 'title',
    descriptionField: 'description',
    get: designsApi.get,
    update: designsApi.update,
    delete: designsApi.delete,
    statusOptions: ['Draft', 'Review', 'Approved'],
    fields: [
      { key: 'design_type', label: 'Design Type', options: ['Architecture', 'Interface', 'Component', 'Data'] },
      { key: 'priority', label: 'Priority', options: ['Low', 'Medium', 'High', 'Critical'] },
      { key: 'status', label: 'Status', options: ['Draft', 'Review', 'Approved'] },
    ],
  },
  risk: {
    singular: 'Risk',
    docType: 'RSK' as DocType,
    queryKey: 'risk',
    listKey: 'risks',
    idField: 'risk_id',
    titleField: 'title',
    descriptionField: 'description',
    get: risksApi.get,
    update: risksApi.update,
    delete: risksApi.delete,
    statusOptions: ['Open', 'Monitoring', 'Mitigated', 'Closed'],
    fields: [
      { key: 'risk_category', label: 'Category', options: ['Technical', 'Business', 'Compliance', 'Schedule', 'Security'] },
      { key: 'severity', label: 'Severity', options: ['Low', 'Medium', 'High', 'Critical'] },
      { key: 'probability', label: 'Probability', options: ['Low', 'Medium', 'High'] },
      { key: 'status', label: 'Status', options: ['Open', 'Monitoring', 'Mitigated', 'Closed'] },
    ],
  },
  change: {
    singular: 'Change Request',
    docType: 'CHG' as DocType,
    queryKey: 'change',
    listKey: 'changes',
    idField: 'change_id',
    titleField: 'title',
    descriptionField: 'description',
    get: changesApi.get,
    update: changesApi.update,
    delete: changesApi.delete,
    statusOptions: ['Submitted', 'Analysis', 'Approved', 'Implemented', 'Rejected'],
    fields: [
      { key: 'change_type', label: 'Change Type', options: ['Enhancement', 'Bug Fix', 'Refactor', 'Compliance'] },
      { key: 'priority', label: 'Priority', options: ['Low', 'Medium', 'High', 'Critical'] },
      { key: 'status', label: 'Status', options: ['Submitted', 'Analysis', 'Approved', 'Implemented', 'Rejected'] },
    ],
  },
  'test-concept': {
    singular: 'Test Concept',
    docType: 'CPT' as DocType,
    queryKey: 'testConcept',
    listKey: 'testConcepts',
    idField: 'concept_id',
    titleField: 'name',
    descriptionField: 'description',
    get: testConceptsApi.get,
    update: testConceptsApi.update,
    delete: testConceptsApi.delete,
    statusOptions: ['Draft', 'Review', 'Approved'],
    fields: [
      { key: 'coverage', label: 'Coverage' },
      { key: 'status', label: 'Status', options: ['Draft', 'Review', 'Approved'] },
    ],
  },
  defect: {
    singular: 'Defect',
    docType: 'DEF' as DocType,
    queryKey: 'defect',
    listKey: 'defects',
    idField: 'defect_id',
    titleField: 'title',
    descriptionField: 'description',
    get: defectsApi.get,
    update: defectsApi.update,
    delete: defectsApi.delete,
    statusOptions: ['Open', 'Triaged', 'In Progress', 'Resolved', 'Verified', 'Closed', 'Rejected', 'Duplicate'],
    fields: [
      { key: 'severity', label: 'Severity', options: ['Low', 'Medium', 'High', 'Critical'] },
      { key: 'priority', label: 'Priority', options: ['Low', 'Medium', 'High', 'Critical'] },
      { key: 'status', label: 'Status', options: ['Open', 'Triaged', 'In Progress', 'Resolved', 'Verified', 'Closed', 'Rejected', 'Duplicate'] },
    ],
  },
} as const

const workflowTransitions: Record<ArtefactKind, Record<string, string[]>> = {
  design: { Draft: ['Review'], Review: ['Approved', 'Draft'], Approved: ['review'] },
  risk: { Open: ['Monitoring', 'Mitigated', 'Closed'], Monitoring: ['Mitigated', 'Closed'], Mitigated: ['Closed', 'Monitoring'], Closed: ['Open'] },
  change: { Submitted: ['Analysis', 'Rejected'], Analysis: ['Approved', 'Rejected'], Approved: ['Implemented', 'Rejected'], Implemented: ['Approved'], Rejected: ['Submitted'] },
  'test-concept': { Draft: ['Review'], Review: ['Approved', 'Draft'], Approved: ['Review'] },
  defect: { Open: ['Triaged', 'Rejected', 'Duplicate'], Triaged: ['In Progress', 'Rejected', 'Duplicate'], 'In Progress': ['Resolved', 'Triaged'], Resolved: ['Verified', 'In Progress'], Verified: ['Closed', 'In Progress'], Closed: ['Open'], Rejected: ['Open'], Duplicate: ['Open'] },
}

export default function ArtefactDetail({ kind, resolvedId }: { kind: ArtefactKind; resolvedId?: number }) {
  const { user } = useAuth()
  const { itemId, prefix } = useParams<{ prefix: string; itemId: string }>()
  const recordId = resolvedId || Number(itemId)
  const config = configs[kind]
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState<DetailTab>('overview')
  const [isEditing, setIsEditing] = useState(false)
  const [commentBody, setCommentBody] = useState('')
  const [form, setForm] = useState<Record<string, string>>({})

  const { data: artefact, isLoading } = useQuery<ArtefactRecord>({
    queryKey: [config.queryKey, recordId],
    queryFn: () => config.get(recordId) as Promise<ArtefactRecord>,
    enabled: !!recordId,
  })

  const projectId = artefact ? (artefact as unknown as Record<string, unknown>).project_id as number : undefined
  const { data: projectData } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  })
  const projectPrefix = prefix || projectData?.prefix || ''

  const { data: comments } = useQuery({
    queryKey: ['artefactComments', kind, recordId],
    queryFn: () => artefactsApi.listComments(kind, recordId),
    enabled: !!recordId,
  })

  const { data: activity } = useQuery({
    queryKey: ['artefactActivity', kind, recordId],
    queryFn: () => artefactsApi.listActivity(kind, recordId),
    enabled: !!recordId,
  })

  const { data: related } = useQuery({
    queryKey: ['artefactRelated', kind, recordId],
    queryFn: () => artefactsApi.getRelated(kind, recordId),
    enabled: !!recordId,
  })

  const { data: syncEvents } = useQuery<SyncEvent[]>({
    queryKey: ['syncEvents', recordId],
    queryFn: () => integrationsApi.listSyncEvents(recordId),
    enabled: !!recordId && kind === 'defect',
  })

  const { data: integrationSettings } = useQuery({
    queryKey: ['integrationSettings', projectId],
    queryFn: () => integrationsApi.listSettings(projectId!),
    enabled: !!projectId && kind === 'defect',
  })

  const trackerSetting = useMemo(() => {
    if (kind !== 'defect' || !integrationSettings) return undefined
    const tracker = (artefact as Defect | undefined)?.external_tracker
    if (!tracker) return undefined
    return integrationSettings.find((s) => s.tracker === tracker)
  }, [kind, integrationSettings, artefact])

  useEffect(() => {
    if (!artefact) return
    const next: Record<string, string> = {}
    Object.entries(artefact as unknown as Record<string, unknown>).forEach(([key, value]) => {
      next[key] = Array.isArray(value) ? value.join(', ') : value == null ? '' : String(value)
    })
    setForm(next)
  }, [artefact])

  const updateMutation = useMutation({
    mutationFn: (payload: Partial<ArtefactRecord>) => config.update(recordId, payload as never) as Promise<ArtefactRecord>,
    onSuccess: (updated: ArtefactRecord) => {
      queryClient.invalidateQueries({ queryKey: [config.queryKey, recordId] })
      queryClient.invalidateQueries({ queryKey: [config.listKey, updated.project_id] })
      queryClient.invalidateQueries({ queryKey: ['project', updated.project_id] })
      queryClient.invalidateQueries({ queryKey: ['artefactActivity', kind, recordId] })
      setIsEditing(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => config.delete(recordId),
    onSuccess: () => {
      if (!artefact) return
      queryClient.invalidateQueries({ queryKey: [config.listKey, artefact.project_id] })
      queryClient.invalidateQueries({ queryKey: ['project', artefact.project_id] })
      navigate(docRegistryListUrl(projectPrefix, config.docType))
    },
  })

  const commentMutation = useMutation({
    mutationFn: () => artefactsApi.createComment(kind, recordId, commentBody),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artefactComments', kind, recordId] })
      queryClient.invalidateQueries({ queryKey: ['artefactActivity', kind, recordId] })
      setCommentBody('')
    },
  })

  const transitionMutation = useMutation({
    mutationFn: (status: string) => artefactsApi.transition(kind, recordId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [config.queryKey, recordId] })
      queryClient.invalidateQueries({ queryKey: ['artefactActivity', kind, recordId] })
      if (artefact) {
        queryClient.invalidateQueries({ queryKey: [config.listKey, artefact.project_id] })
      }
    },
  })

  const refreshExternalMutation = useMutation({
    mutationFn: () => integrationsApi.refreshExternal(recordId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [config.queryKey, recordId] })
      queryClient.invalidateQueries({ queryKey: ['syncEvents', recordId] })
      queryClient.invalidateQueries({ queryKey: ['artefactActivity', kind, recordId] })
    },
  })

  const artefactRecord = artefact as unknown as Record<string, unknown> | undefined
  const allowedTransitions = artefact ? workflowTransitions[kind][String(artefact.status)] ?? [] : []

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    const payload: Record<string, unknown> = {}
    for (const field of config.fields) {
      const value = form[field.key] ?? ''
      if (field.key === 'coverage') {
        payload[field.key] = Number(value) || 0
      } else {
        payload[field.key] = value || null
      }
    }
    if (kind === 'defect') {
      payload.title = (form.title ?? '').trim() || (artefactRecord?.[config.titleField] as string) || ''
      payload.description = form.description ?? null
      payload.resolution_summary = (form.resolution_summary ?? '').trim() || null
    }
    updateMutation.mutate(payload as Partial<ArtefactRecord>)
  }

  if (isLoading) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  if (!artefact || !artefactRecord) return <div className="text-center text-destructive">{config.singular} not found.</div>

  const code = String(artefactRecord[config.idField] ?? '')
  const title = String(artefactRecord[config.titleField] ?? config.singular)
  const description = String(artefactRecord[config.descriptionField] ?? '')
  const editUrl = docEditUrl(projectPrefix, config.docType, code)
  const canEditDocs = user?.role === 'admin' || user?.role === 'maintainer'

  return (
    <DocDetailShell
      projectPrefix={projectPrefix}
      docType={config.docType}
      docCode={code}
      title={title}
      status={String(artefact.status)}
      actions={canEditDocs ? (
        <>
          <button onClick={() => {
            if (isEditing) {
              setIsEditing(false)
            } else if (kind === 'defect') {
              setActiveTab('overview')
              setIsEditing(true)
            } else {
              navigate(`${editUrl}?type=${config.docType}`)
            }
          }} className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 text-sm">
            <Pencil className="h-4 w-4 mr-2" />
            {isEditing ? 'Cancel' : 'Edit'}
          </button>
          <button onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending} className="inline-flex items-center px-4 py-2 border border-red-300 text-red-600 rounded-md hover:bg-red-50 text-sm disabled:opacity-50">
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </button>
        </>
      ) : undefined}
      rightRail={
        <>
          <SectionCard title="Workflow">
            <div className="space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Current Status</div>
                <StatusBadge status={String(artefact.status)} />
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-2">Available Transitions</div>
                {allowedTransitions.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No transition actions available.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {allowedTransitions.map((status) => (
                      <button key={status} onClick={() => transitionMutation.mutate(status)} disabled={transitionMutation.isPending} className="px-3 py-2 rounded-md border border-input text-sm hover:bg-accent/40 disabled:opacity-50">
                        Move to {status}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Details">
            <div className="space-y-4">
              {config.fields.filter((f) => f.key !== 'status').map((field) => (
                <div key={field.key}>
                  <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">{field.label}</div>
                  <div className="text-foreground text-sm">{String(artefactRecord[field.key] ?? '-')}</div>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Metadata">
            <div className="space-y-4">
              <MetaItem label="ID" value={code} mono />
              <MetaItem label="Project" value={related?.project ? `${related.project.prefix} · ${related.project.name}` : `#${artefact.project_id}`} />
              <MetaItem label="Created" value={formatDateTime(artefact.created_at) + ' ago'} />
              <MetaItem label="Updated" value={formatDateTime(artefact.updated_at) + ' ago'} />
            </div>
          </SectionCard>

          <SectionCard title="Quick Links">
            <div className="space-y-3 text-sm">
              <Link to={docRegistryListUrl(projectPrefix, config.docType)} className="block text-primary hover:text-primary/80">Back to project {config.singular.toLowerCase()} list</Link>
              {related?.project && <Link to={`/projects/${related.project.prefix}`} className="block text-primary hover:text-primary/80">Open project workspace</Link>}
            </div>
          </SectionCard>
        </>
      }
    >
      <div className="border-b border-border overflow-x-auto">
        <nav className="flex gap-6 min-w-max">
          {[
            { key: 'overview' as const, label: 'Overview', icon: Pencil },
            { key: 'comments' as const, label: 'Comments', icon: MessageSquare },
            { key: 'activity' as const, label: 'Activity', icon: History },
            { key: 'related' as const, label: 'Related', icon: GitBranch },
            ...(kind === 'defect' ? [{ key: 'sync' as const, label: 'Sync Log', icon: ArrowUpDown }] : []),
          ].map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)} className={`flex items-center py-3 px-1 border-b-2 text-sm font-medium ${activeTab === tab.key ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
              <tab.icon className="h-4 w-4 mr-2" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'overview' && (
        isEditing ? (
          <form onSubmit={handleSave} className="bg-card rounded-lg shadow-elegant p-6 space-y-5">
            {kind === 'defect' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Title</label>
                  <input
                    value={form.title ?? ''}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    title="Defect title"
                    placeholder="Short defect summary"
                    className="w-full px-3 py-2 bg-background border border-input rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Description</label>
                  <textarea
                    rows={4}
                    value={form.description ?? ''}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    title="Defect description"
                    placeholder="What is broken? Steps to reproduce?"
                    className="w-full px-3 py-2 bg-background border border-input rounded-md"
                  />
                </div>
              </>
            )}
            {config.fields.map((field) => (
              <div key={field.key}>
                <label className="block text-sm font-medium text-foreground mb-1">{field.label}</label>
                {'options' in field && field.options ? (
                  <select value={form[field.key] ?? ''} onChange={(e) => setForm({ ...form, [field.key]: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md">
                    {field.options.map((option: string) => <option key={option}>{option}</option>)}
                  </select>
                ) : (
                  <input value={form[field.key] ?? ''} onChange={(e) => setForm({ ...form, [field.key]: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md" />
                )}
              </div>
            ))}
            {kind === 'defect' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Resolution Summary</label>
                  <textarea
                    rows={3}
                    value={form.resolution_summary ?? ''}
                    onChange={(e) => setForm({ ...form, resolution_summary: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md"
                    placeholder="What was done to resolve this defect?"
                  />
                </div>
              </>
            )}
            {updateMutation.isError && (
              <div className="text-sm text-destructive">{extractApiErrorMessage(updateMutation.error)}</div>
            )}
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setIsEditing(false)} className="px-4 py-2 border border-input rounded-md">Cancel</button>
              <button type="submit" disabled={updateMutation.isPending} className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50">{updateMutation.isPending ? 'Saving...' : 'Save Changes'}</button>
            </div>
          </form>
        ) : (
          <div className="space-y-6">
            {kind === 'defect' ? (
              <SectionCard title="Description">
                <p className="text-foreground whitespace-pre-wrap leading-relaxed">{description || 'No description provided.'}</p>
              </SectionCard>
            ) : (artefactRecord.content_json as Record<string, unknown> | null) ? (
              <SectionCard title="Content">
                <DocEditor
                  content={artefactRecord.content_json as Record<string, unknown>}
                  editable={false}
                  minHeight="min-h-[120px]"
                  className="border-0"
                />
              </SectionCard>
            ) : (
              <SectionCard title="Description">
                <p className="text-foreground whitespace-pre-wrap leading-relaxed">{description || 'No description provided.'}</p>
              </SectionCard>
            )}

            {kind === 'risk' && (artefactRecord as unknown as RiskItem).mitigation && (
              <SectionCard title="Mitigation">
                <p className="text-foreground whitespace-pre-wrap leading-relaxed">{String((artefactRecord as unknown as RiskItem).mitigation)}</p>
              </SectionCard>
            )}

            {kind === 'change' && ((artefactRecord as unknown as ChangeRequest).impact_assessment || (artefactRecord as unknown as ChangeRequest).justification) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {(artefactRecord as unknown as ChangeRequest).impact_assessment && (
                  <SectionCard title="Impact Assessment">
                    <p className="text-foreground whitespace-pre-wrap leading-relaxed">{String((artefactRecord as unknown as ChangeRequest).impact_assessment)}</p>
                  </SectionCard>
                )}
                {(artefactRecord as unknown as ChangeRequest).justification && (
                  <SectionCard title="Justification">
                    <p className="text-foreground whitespace-pre-wrap leading-relaxed">{String((artefactRecord as unknown as ChangeRequest).justification)}</p>
                  </SectionCard>
                )}
              </div>
            )}

            {kind === 'defect' && (artefactRecord as unknown as Defect).resolution_summary && (
              <SectionCard title="Resolution">
                <p className="text-foreground whitespace-pre-wrap leading-relaxed">{String((artefactRecord as unknown as Defect).resolution_summary)}</p>
              </SectionCard>
            )}

            {kind === 'defect' && (
              <ExternalIssueCard
                defect={artefactRecord as unknown as Defect}
                projectPrefix={projectPrefix}
                hasStoredToken={!!trackerSetting?.has_token}
                onRefresh={() => refreshExternalMutation.mutate()}
                refreshing={refreshExternalMutation.isPending}
                refreshError={refreshExternalMutation.isError ? extractApiErrorMessage(refreshExternalMutation.error) : null}
              />
            )}

            <DocumentLinksPanel
              projectId={artefact.project_id}
              projectPrefix={projectPrefix}
              sourceType={SOURCE_TYPE_CODES[kind]}
              sourceId={recordId}
            />
          </div>
        )
      )}

      {activeTab === 'comments' && (
        <div className="space-y-4">
          <SectionCard title="Add Comment">
            <div className="space-y-3">
              <textarea value={commentBody} onChange={(e) => setCommentBody(e.target.value)} rows={4} className="w-full px-3 py-2 bg-background border border-input rounded-md" placeholder={`Discuss this ${config.singular.toLowerCase()}...`} />
              <div className="flex justify-end">
                <button onClick={() => commentMutation.mutate()} disabled={!commentBody.trim() || commentMutation.isPending} className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 text-sm">
                  {commentMutation.isPending ? 'Posting...' : 'Post Comment'}
                </button>
              </div>
            </div>
          </SectionCard>
          <SectionCard title={`Discussion (${comments?.length ?? 0})`}>
            {!comments || comments.length === 0 ? (
              <p className="text-muted-foreground">No comments yet.</p>
            ) : (
              <div className="space-y-4">
                {comments.map((comment) => (
                  <div key={comment.id} className="rounded-lg border border-border p-4 bg-background/60">
                    <div className="flex items-center justify-between gap-4">
                      <div className="font-medium text-foreground">{comment.author_name}</div>
                      <div className="text-xs text-muted-foreground">{formatDateTime(comment.created_at)} ago</div>
                    </div>
                    <p className="text-foreground mt-3 whitespace-pre-wrap leading-relaxed">{comment.body}</p>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      )}

      {activeTab === 'activity' && (
        <SectionCard title={`Activity (${activity?.length ?? 0})`}>
          {!activity || activity.length === 0 ? (
            <p className="text-muted-foreground">No activity recorded yet.</p>
          ) : (
            <div className="space-y-4">
              {activity.map((event) => (
                <div key={event.id} className="flex gap-4">
                  <div className="mt-1 h-2.5 w-2.5 rounded-full bg-primary shrink-0" />
                  <div>
                    <div className="font-medium text-foreground">{event.summary}</div>
                    <div className="text-xs text-muted-foreground mt-1">{event.event_type} · {formatDateTime(event.created_at)} ago</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}

      {activeTab === 'related' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <SectionCard title={`Requirements (${related?.linked_requirements.length ?? 0})`}>
            {!related || related.linked_requirements.length === 0 ? <p className="text-muted-foreground">No linked requirements.</p> : (
              <div className="flex flex-wrap gap-1">
                {related.linked_requirements.map((item) => (
                  <Link key={item.id} to={docUrl(projectPrefix, 'REQ', item.req_id)} className="font-mono text-xs text-primary hover:underline">
                    {item.req_id}
                  </Link>
                ))}
              </div>
            )}
          </SectionCard>
          <SectionCard title={`Test Cases (${related?.related_test_cases.length ?? 0})`}>
            {!related || related.related_test_cases.length === 0 ? <p className="text-muted-foreground">No related test cases.</p> : (
              <div className="flex flex-wrap gap-1">
                {related.related_test_cases.map((item) => (
                  <Link key={item.id} to={docUrl(projectPrefix, 'TC', item.tc_id)} className="font-mono text-xs text-primary hover:underline">
                    {item.tc_id}
                  </Link>
                ))}
              </div>
            )}
          </SectionCard>
          <SectionCard title={`Documents (${related?.related_documents.length ?? 0})`}>
            {!related || related.related_documents.length === 0 ? <p className="text-muted-foreground">No related documents.</p> : (
              <div className="flex flex-wrap gap-1">
                {related.related_documents.map((item) => (
                  <Link
                    key={item.id}
                    to={item.doc_id ? docUrl(projectPrefix, item.doc_type as DocType, item.doc_id) : '#'}
                    className="font-mono text-xs text-primary hover:underline"
                  >
                    {item.doc_id || item.title}
                  </Link>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      )}
      {activeTab === 'sync' && kind === 'defect' && (
        <SectionCard title={`Sync Events (${syncEvents?.length ?? 0})`}>
          {!syncEvents || syncEvents.length === 0 ? (
            <p className="text-muted-foreground">No sync events recorded yet.</p>
          ) : (
            <div className="space-y-3">
              {syncEvents.map((event) => (
                <div key={event.id} className="flex gap-4 items-start">
                  <div className={`mt-1 h-2.5 w-2.5 rounded-full shrink-0 ${event.success ? 'bg-green-500' : 'bg-red-500'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-sm">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${event.direction === 'inbound' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'}`}>
                        {event.direction}
                      </span>
                      <span className="font-medium text-foreground">{event.event_type}</span>
                      <span className="text-muted-foreground">via {event.tracker}</span>
                    </div>
                    {event.payload_summary && <div className="text-xs text-muted-foreground mt-1">{event.payload_summary}</div>}
                    {event.error_message && <div className="text-xs text-destructive mt-1">{event.error_message}</div>}
                    <div className="text-xs text-muted-foreground mt-1">{formatDateTime(event.created_at)} ago</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}
    </DocDetailShell>
  )
}

function ExternalIssueCard({
  defect,
  projectPrefix,
  hasStoredToken,
  onRefresh,
  refreshing,
  refreshError,
}: {
  defect: Defect
  projectPrefix: string
  hasStoredToken: boolean
  onRefresh: () => void
  refreshing: boolean
  refreshError: string | null
}) {
  const tracker = defect.external_tracker
  const trackerLabel = tracker === 'github' ? 'GitHub' : tracker === 'gitlab' ? 'GitLab' : null
  const webhookPath = tracker === 'gitlab' ? '/api/integrations/gitlab/webhook' : '/api/integrations/github/webhook'

  if (!tracker) {
    return (
      <SectionCard title="External Issue">
        <p className="text-sm text-muted-foreground">No external issue linked.</p>
      </SectionCard>
    )
  }

  return (
    <SectionCard title="External Issue">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          {defect.external_issue_url ? (
            <a
              href={defect.external_issue_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-primary hover:text-primary/80 text-sm font-medium"
            >
              <ExternalLink className="h-4 w-4" />
              {defect.external_repo_full_name || 'External issue'}
              {defect.external_issue_number ? ` #${defect.external_issue_number}` : ''}
            </a>
          ) : (
            <span className="text-sm text-muted-foreground">
              {defect.external_repo_full_name || trackerLabel}
              {defect.external_issue_number ? ` #${defect.external_issue_number}` : ''}
            </span>
          )}
          {defect.external_issue_state && (
            <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
              {defect.external_issue_state}
            </span>
          )}
          <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">{trackerLabel}</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing || !hasStoredToken}
            title={hasStoredToken ? `Refresh state from ${trackerLabel}` : `Add a ${trackerLabel} token in project settings to refresh`}
            className="inline-flex items-center gap-2 px-3 py-1.5 border border-input rounded-md text-sm hover:bg-accent/40 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh from tracker'}
          </button>
        </div>

        {!hasStoredToken && (
          <p className="text-xs text-amber-700 dark:text-amber-400">
            No {trackerLabel} token configured for this project. Add one in{' '}
            <Link to={`/projects/${projectPrefix}/edit`} className="underline hover:no-underline">
              project settings
            </Link>{' '}
            to enable refresh and outbound sync.
          </p>
        )}

        {refreshError && <p className="text-xs text-destructive">{refreshError}</p>}

        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer select-none hover:text-foreground">
            Webhook setup ({trackerLabel})
          </summary>
          <p className="mt-2">
            Configure your repository to POST issue events to{' '}
            <code className="font-mono text-foreground">{webhookPath}</code> using the secret stored in project
            settings. Bloom updates the linked defect when the webhook fires.
          </p>
        </details>
      </div>
    </SectionCard>
  )
}
