import { ReactNode, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, GitBranch, History, MessageSquare, Pencil, Trash2, FileEdit } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { DocEditor } from '../components/editor'

import {
  artefactsApi,
  ChangeRequest,
  changesApi,
  DesignItem,
  designsApi,
  RiskItem,
  risksApi,
  TestConcept,
  testConceptsApi,
  projectsApi,
} from '../api/client'

type ArtefactKind = 'design' | 'risk' | 'change' | 'test-concept'
type ArtefactRecord = DesignItem | RiskItem | ChangeRequest | TestConcept
type DetailTab = 'overview' | 'comments' | 'activity' | 'related'

const configs = {
  design: {
    singular: 'Design Item',
    route: 'designs',
    queryKey: 'design',
    listKey: 'designs',
    tabKey: 'design',
    idField: 'design_id',
    titleField: 'title',
    descriptionField: 'description',
    get: designsApi.get,
    update: designsApi.update,
    delete: designsApi.delete,
    statusOptions: ['Draft', 'Review', 'Approved'],
    fields: [
      { key: 'title', label: 'Title' },
      { key: 'description', label: 'Description', multiline: true },
      { key: 'design_type', label: 'Design Type', options: ['Architecture', 'Interface', 'Component', 'Data'] },
      { key: 'priority', label: 'Priority', options: ['Low', 'Medium', 'High', 'Critical'] },
      { key: 'status', label: 'Status', options: ['Draft', 'Review', 'Approved'] },
      { key: 'linked_requirement_id', label: 'Linked Requirement ID' },
    ],
  },
  risk: {
    singular: 'Risk',
    route: 'risks',
    queryKey: 'risk',
    listKey: 'risks',
    tabKey: 'risks',
    idField: 'risk_id',
    titleField: 'title',
    descriptionField: 'description',
    get: risksApi.get,
    update: risksApi.update,
    delete: risksApi.delete,
    statusOptions: ['Open', 'Monitoring', 'Mitigated', 'Closed'],
    fields: [
      { key: 'title', label: 'Title' },
      { key: 'description', label: 'Description', multiline: true },
      { key: 'mitigation', label: 'Mitigation', multiline: true },
      { key: 'risk_category', label: 'Category', options: ['Technical', 'Business', 'Compliance', 'Schedule', 'Security'] },
      { key: 'severity', label: 'Severity', options: ['Low', 'Medium', 'High', 'Critical'] },
      { key: 'probability', label: 'Probability', options: ['Low', 'Medium', 'High'] },
      { key: 'status', label: 'Status', options: ['Open', 'Monitoring', 'Mitigated', 'Closed'] },
      { key: 'linked_requirement_id', label: 'Linked Requirement ID' },
    ],
  },
  change: {
    singular: 'Change Request',
    route: 'changes',
    queryKey: 'change',
    listKey: 'changes',
    tabKey: 'changes',
    idField: 'change_id',
    titleField: 'title',
    descriptionField: 'description',
    get: changesApi.get,
    update: changesApi.update,
    delete: changesApi.delete,
    statusOptions: ['Submitted', 'Analysis', 'Approved', 'Implemented', 'Rejected'],
    fields: [
      { key: 'title', label: 'Title' },
      { key: 'description', label: 'Description', multiline: true },
      { key: 'impact_assessment', label: 'Impact Assessment', multiline: true },
      { key: 'justification', label: 'Justification', multiline: true },
      { key: 'change_type', label: 'Change Type', options: ['Enhancement', 'Bug Fix', 'Refactor', 'Compliance'] },
      { key: 'priority', label: 'Priority', options: ['Low', 'Medium', 'High', 'Critical'] },
      { key: 'status', label: 'Status', options: ['Submitted', 'Analysis', 'Approved', 'Implemented', 'Rejected'] },
    ],
  },
  'test-concept': {
    singular: 'Test Concept',
    route: 'test-concepts',
    queryKey: 'testConcept',
    listKey: 'testConcepts',
    tabKey: 'test-concepts',
    idField: 'concept_id',
    titleField: 'name',
    descriptionField: 'description',
    get: testConceptsApi.get,
    update: testConceptsApi.update,
    delete: testConceptsApi.delete,
    statusOptions: ['Draft', 'Review', 'Approved'],
    fields: [
      { key: 'name', label: 'Name' },
      { key: 'description', label: 'Description', multiline: true },
      { key: 'coverage', label: 'Coverage' },
      { key: 'status', label: 'Status', options: ['Draft', 'Review', 'Approved'] },
      { key: 'linked_requirement_ids', label: 'Linked Requirement IDs' },
    ],
  },
} as const

const workflowTransitions: Record<ArtefactKind, Record<string, string[]>> = {
  design: { Draft: ['Review'], Review: ['Approved', 'Draft'], Approved: ['Review'] },
  risk: { Open: ['Monitoring', 'Mitigated', 'Closed'], Monitoring: ['Mitigated', 'Closed'], Mitigated: ['Closed', 'Monitoring'], Closed: ['Open'] },
  change: { Submitted: ['Analysis', 'Rejected'], Analysis: ['Approved', 'Rejected'], Approved: ['Implemented', 'Rejected'], Implemented: ['Approved'], Rejected: ['Submitted'] },
  'test-concept': { Draft: ['Review'], Review: ['Approved', 'Draft'], Approved: ['Review'] },
}

export default function ArtefactDetail({ kind, resolvedId }: { kind: ArtefactKind; resolvedId?: number }) {
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
      navigate(`/projects/${projectPrefix}?tab=${config.tabKey}`)
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

  const artefactRecord = artefact as unknown as Record<string, unknown> | undefined
  const allowedTransitions = artefact ? workflowTransitions[kind][String(artefact.status)] ?? [] : []

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    const payload: Record<string, unknown> = {}
    for (const field of config.fields) {
      const value = form[field.key] ?? ''
      if (field.key === 'linked_requirement_ids') {
        payload[field.key] = value ? value.split(',').map((item) => Number(item.trim())).filter(Boolean) : []
      } else if (field.key === 'linked_requirement_id') {
        payload[field.key] = value ? Number(value) : null
      } else if (field.key === 'coverage') {
        payload[field.key] = Number(value) || 0
      } else {
        payload[field.key] = value || null
      }
    }
    updateMutation.mutate(payload as Partial<ArtefactRecord>)
  }

  if (isLoading) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  if (!artefact || !artefactRecord) return <div className="text-center text-destructive">{config.singular} not found.</div>

  const code = String(artefactRecord[config.idField] ?? '')
  const title = String(artefactRecord[config.titleField] ?? config.singular)
  const description = String(artefactRecord[config.descriptionField] ?? '')

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <Link to={`/projects/${projectPrefix}?tab=${config.tabKey}`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-mono text-sm text-primary font-semibold">{code}</span>
              <StatusBadge value={String(artefact.status)} />
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{config.singular}</span>
            </div>
            <h2 className="text-3xl font-bold text-foreground mt-2">{title}</h2>
            <p className="text-muted-foreground mt-2 max-w-3xl">{description || `No ${config.descriptionField.replace('_', ' ')} provided.`}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setIsEditing((value) => !value)} className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 text-sm">
            <Pencil className="h-4 w-4 mr-2" />
            {isEditing ? 'Cancel' : 'Edit'}
          </button>
          {!isEditing && (
            <button
              onClick={() => {
                const typeMap: Record<ArtefactKind, string> = { design: 'DES', risk: 'RSK', change: 'CHG', 'test-concept': 'TCO' }
                navigate(`/projects/${projectPrefix}/docs/${code}/edit?type=${typeMap[kind]}`)
              }}
              className="inline-flex items-center px-4 py-2 border border-primary text-primary rounded-md hover:bg-primary/10 text-sm"
            >
              <FileEdit className="h-4 w-4 mr-2" />
              Full Editor
            </button>
          )}
          <button onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending} className="inline-flex items-center px-4 py-2 border border-red-300 text-red-600 rounded-md hover:bg-red-50 text-sm disabled:opacity-50">
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px] gap-6">
        <div className="space-y-6">
          <div className="border-b border-border overflow-x-auto">
            <nav className="flex gap-6 min-w-max">
              {[
                { key: 'overview' as const, label: 'Overview', icon: Pencil },
                { key: 'comments' as const, label: 'Comments', icon: MessageSquare },
                { key: 'activity' as const, label: 'Activity', icon: History },
                { key: 'related' as const, label: 'Related', icon: GitBranch },
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
                {config.fields.map((field) => (
                  <div key={field.key}>
                    <label className="block text-sm font-medium text-foreground mb-1">{field.label}</label>
                    {'multiline' in field && field.multiline ? (
                      <textarea value={form[field.key] ?? ''} onChange={(e) => setForm({ ...form, [field.key]: e.target.value })} rows={4} className="w-full px-3 py-2 bg-background border border-input rounded-md" />
                    ) : 'options' in field && field.options ? (
                      <select value={form[field.key] ?? ''} onChange={(e) => setForm({ ...form, [field.key]: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md">
                        {field.options.map((option: string) => <option key={option}>{option}</option>)}
                      </select>
                    ) : (
                      <input value={form[field.key] ?? ''} onChange={(e) => setForm({ ...form, [field.key]: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md" />
                    )}
                  </div>
                ))}
                <div className="flex justify-end gap-3">
                  <button type="button" onClick={() => setIsEditing(false)} className="px-4 py-2 border border-input rounded-md">Cancel</button>
                  <button type="submit" disabled={updateMutation.isPending} className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50">{updateMutation.isPending ? 'Saving...' : 'Save Changes'}</button>
                </div>
              </form>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <SectionCard title="Description">
                  {(artefactRecord.content_json as Record<string, unknown> | null) ? (
                    <DocEditor
                      content={artefactRecord.content_json as Record<string, unknown>}
                      editable={false}
                      minHeight="min-h-[100px]"
                      className="border-0"
                    />
                  ) : (
                    <p className="text-foreground whitespace-pre-wrap leading-relaxed">{description || 'No description provided.'}</p>
                  )}
                </SectionCard>
                <SectionCard title="Fields">
                  <div className="space-y-4">
                    {config.fields.filter((field) => field.key !== config.descriptionField).map((field) => (
                      <div key={field.key}>
                        <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">{field.label}</div>
                        <div className="text-foreground whitespace-pre-wrap">{String(artefactRecord[field.key] ?? '-')}</div>
                      </div>
                    ))}
                  </div>
                </SectionCard>
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
                          <div className="text-xs text-muted-foreground">{formatDistanceToNow(new Date(comment.created_at))} ago</div>
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
                        <div className="text-xs text-muted-foreground mt-1">{event.event_type} · {formatDistanceToNow(new Date(event.created_at))} ago</div>
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
                  <div className="space-y-3">
                    {related.linked_requirements.map((item) => (
                      <Link key={item.id} to={`/projects/${projectPrefix}/docs/${item.req_id}`} className="block rounded-lg border border-border p-3 hover:bg-accent/40 transition-colors">
                        <div className="font-mono text-xs text-primary">{item.req_id}</div>
                        <div className="font-medium text-foreground mt-1">{item.title}</div>
                        <div className="text-xs text-muted-foreground mt-1">{item.status}</div>
                      </Link>
                    ))}
                  </div>
                )}
              </SectionCard>
              <SectionCard title={`Test Cases (${related?.related_test_cases.length ?? 0})`}>
                {!related || related.related_test_cases.length === 0 ? <p className="text-muted-foreground">No related test cases.</p> : (
                  <div className="space-y-3">
                    {related.related_test_cases.map((item) => (
                      <Link key={item.id} to={`/projects/${projectPrefix}/docs/${item.tc_id}`} className="block rounded-lg border border-border p-3 hover:bg-accent/40 transition-colors">
                        <div className="font-mono text-xs text-primary">{item.tc_id}</div>
                        <div className="font-medium text-foreground mt-1">{item.title}</div>
                        <div className="text-xs text-muted-foreground mt-1">{item.status}</div>
                      </Link>
                    ))}
                  </div>
                )}
              </SectionCard>
              <SectionCard title={`Documents (${related?.related_documents.length ?? 0})`}>
                {!related || related.related_documents.length === 0 ? <p className="text-muted-foreground">No related documents.</p> : (
                  <div className="space-y-3">
                    {related.related_documents.map((item) => (
                      <Link key={item.id} to={`/documents/${item.id}`} className="block rounded-lg border border-border p-3 hover:bg-accent/40 transition-colors">
                        <div className="font-medium text-foreground">{item.title}</div>
                        <div className="text-xs text-muted-foreground mt-1">{item.doc_type} · {item.status}</div>
                        {item.matched_sections.length > 0 && <div className="text-xs text-primary mt-2">Sections: {item.matched_sections.join(', ')}</div>}
                      </Link>
                    ))}
                  </div>
                )}
              </SectionCard>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <SectionCard title="Workflow">
            <div className="space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Current Status</div>
                <StatusBadge value={String(artefact.status)} />
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

          <SectionCard title="Metadata">
            <div className="space-y-4">
              <MetaItem label="ID" value={code} mono />
              <MetaItem label="Project" value={related?.project ? `${related.project.prefix} · ${related.project.name}` : `#${artefact.project_id}`} />
              <MetaItem label="Created" value={formatDistanceToNow(new Date(artefact.created_at)) + ' ago'} />
              <MetaItem label="Updated" value={formatDistanceToNow(new Date(artefact.updated_at)) + ' ago'} />
            </div>
          </SectionCard>

          <SectionCard title="Quick Links">
            <div className="space-y-3 text-sm">
              <Link to={`/projects/${projectPrefix}?tab=${config.tabKey}`} className="block text-primary hover:text-primary/80">Back to project {config.singular.toLowerCase()} list</Link>
              {related?.project && <Link to={`/projects/${related.project.prefix}`} className="block text-primary hover:text-primary/80">Open project workspace</Link>}
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  )
}

function SectionCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="bg-card rounded-lg shadow-elegant p-6">
      <h3 className="text-lg font-semibold text-foreground mb-4">{title}</h3>
      {children}
    </div>
  )
}

function MetaItem({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">{label}</div>
      <div className={`${mono ? 'font-mono' : ''} text-foreground`}>{value}</div>
    </div>
  )
}

function StatusBadge({ value }: { value: string }) {
  const palette: Record<string, string> = {
    Draft: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
    Review: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Approved: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Open: 'bg-red-500/10 text-red-700 dark:text-red-400',
    Monitoring: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Mitigated: 'bg-teal-500/10 text-teal-700 dark:text-teal-400',
    Closed: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
    Submitted: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Analysis: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
    Implemented: 'bg-teal-500/10 text-teal-700 dark:text-teal-400',
    Rejected: 'bg-red-500/10 text-red-700 dark:text-red-400',
  }
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${palette[value] || 'bg-muted text-muted-foreground'}`}>{value}</span>
}
