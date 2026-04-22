import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  type ArtefactLink,
  type DocShell,
  type TcsRow,
  docsApi,
  linksApi,
  projectsApi,
  testCasesApi,
  usersApi,
} from '../api/client'
import { TcsArteTable } from '../components/TcsArteTable'
import { normalizeTcsRows } from '../utils/tcs'
import { ArrowLeft, FileText, Link2, Pencil, Search, UserCheck, UserCog, X } from 'lucide-react'
import { formatDateTime } from '../test/date-utils'

const DOC_TYPE_LABELS: Record<string, string> = {
  REQ: 'Requirement',
  TC: 'Test Case',
  DOC: 'Specification',
  DES: 'Design',
  RSK: 'Risk',
  CHG: 'Change',
  TCO: 'Test Concept',
}

const LINK_ROLES = ['verifies', 'implements', 'references', 'depends_on', 'impacts', 'blocks'] as const

function normalizeSteps(steps: unknown): TcsRow[] {
  return normalizeTcsRows(steps) as TcsRow[]
}

export default function TestCaseDetail({ resolvedId }: { resolvedId?: number } = {}) {
  const { itemId } = useParams<{ prefix: string; itemId: string }>()
  const tcId = resolvedId || parseInt(itemId || '0')
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const { data: testCase, isLoading, error } = useQuery({
    queryKey: ['testCase', tcId],
    queryFn: () => testCasesApi.get(tcId),
    enabled: !!tcId,
  })

  const { data: project } = useQuery({
    queryKey: ['project', testCase?.project_id],
    queryFn: () => projectsApi.get(testCase!.project_id),
    enabled: !!testCase?.project_id,
  })

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })

  const markReviewedMutation = useMutation({
    mutationFn: (reviewedById: number) => testCasesApi.setReviewed(tcId, reviewedById),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCase', tcId] })
    },
  })

  const markApprovedMutation = useMutation({
    mutationFn: (approvedById: number) => testCasesApi.setApproved(tcId, approvedById),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCase', tcId] })
    },
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (error || !testCase) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Test Case Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Projects
        </Link>
      </div>
    )
  }

  const projectPrefix = project?.prefix || ''
  const tcsRows = normalizeSteps(testCase.steps)

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${projectPrefix}`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <div className="flex items-center space-x-3">
              <span className="font-mono text-sm text-primary font-semibold">{testCase.tc_id}</span>
              <TcStatusBadge status={testCase.status} />
            </div>
            <h2 className="text-2xl font-bold text-foreground mt-1">{testCase.title}</h2>
          </div>
        </div>
        <button
          onClick={() => navigate(`/projects/${projectPrefix}/docs/${testCase.tc_id}/edit?type=TC`)}
          className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
        >
          <Pencil className="h-4 w-4 mr-2" />
          Edit
        </button>
      </div>

      {testCase.description && (
        <div className="bg-card rounded-lg shadow-elegant p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Description</h3>
          <p className="text-foreground whitespace-pre-wrap">{testCase.description}</p>
        </div>
      )}

      {tcsRows.length > 0 && (
        <TcsArteTable rows={tcsRows} onChange={() => {}} editable={false} />
      )}

      {project && (
        <DocumentLinksPanel
          projectId={testCase.project_id}
          projectPrefix={project.prefix}
          sourceId={testCase.id}
        />
      )}

      <div className="bg-card rounded-lg shadow-elegant p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-md border border-border p-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Review</p>
          <p className="text-sm text-foreground">Assigned reviewer: {resolveUserName(users, testCase.reviewer_id)}</p>
          <p className="text-xs text-muted-foreground mt-1">Reviewed by: {resolveUserName(users, testCase.reviewed_by_id)}</p>
          {testCase.reviewed_at && <p className="text-xs text-muted-foreground mt-1">At {formatDateTime(testCase.reviewed_at)}</p>}
          <button
            disabled={!testCase.reviewer_id || markReviewedMutation.isPending}
            onClick={() => testCase.reviewer_id && markReviewedMutation.mutate(testCase.reviewer_id)}
            className="mt-3 inline-flex items-center px-3 py-1.5 rounded-md bg-amber-500/90 text-white text-xs font-medium hover:bg-amber-500 disabled:opacity-50"
          >
            <UserCheck className="h-3.5 w-3.5 mr-1" />
            Mark Reviewed
          </button>
        </div>
        <div className="rounded-md border border-border p-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Approval</p>
          <p className="text-sm text-foreground">Assigned approver: {resolveUserName(users, testCase.approver_id)}</p>
          <p className="text-xs text-muted-foreground mt-1">Approved by: {resolveUserName(users, testCase.approved_by_id)}</p>
          {testCase.approved_at && <p className="text-xs text-muted-foreground mt-1">At {formatDateTime(testCase.approved_at)}</p>}
          <button
            disabled={!testCase.approver_id || markApprovedMutation.isPending}
            onClick={() => testCase.approver_id && markApprovedMutation.mutate(testCase.approver_id)}
            className="mt-3 inline-flex items-center px-3 py-1.5 rounded-md bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            <UserCog className="h-3.5 w-3.5 mr-1" />
            Mark Approved
          </button>
        </div>
      </div>

      <MembershipPanel
        title="Contained In Suites"
        countLabel={`${testCase.suite_memberships?.length || 0} suite${(testCase.suite_memberships?.length || 0) !== 1 ? 's' : ''}`}
        emptyText="This test case is not part of any suite yet."
      >
        {testCase.suite_memberships?.map((suite) => (
          <div key={suite.id} className="px-6 py-4 flex items-center justify-between">
            <div>
              <div className="font-mono text-sm text-primary">{suite.suite_id}</div>
              <div className="text-foreground mt-1">{suite.name}</div>
            </div>
            <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{suite.status}</span>
          </div>
        ))}
      </MembershipPanel>

      <MembershipPanel
        title="Included In Campaign Scopes"
        countLabel={`${testCase.campaign_memberships?.length || 0} campaign${(testCase.campaign_memberships?.length || 0) !== 1 ? 's' : ''}`}
        emptyText="This test case is not included in any campaign scope yet."
      >
        {testCase.campaign_memberships?.map((campaign) => (
          <div key={campaign.id} className="px-6 py-4 flex items-center justify-between">
            <div className="text-foreground">{campaign.name}</div>
            <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{campaign.status}</span>
          </div>
        ))}
      </MembershipPanel>

      <div className="text-sm text-muted-foreground flex items-center space-x-6">
        <span>Created {formatDateTime(testCase.created_at)} ago</span>
        <span>Updated {formatDateTime(testCase.updated_at)} ago</span>
      </div>
    </div>
  )
}

function DocumentLinksPanel({ projectId, projectPrefix, sourceId }: { projectId: number; projectPrefix: string; sourceId: number }) {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)

  const { data: docs } = useQuery({
    queryKey: ['all-docs', projectPrefix, 'tc-links'],
    queryFn: () => docsApi.list(projectPrefix),
    enabled: !!projectPrefix,
  })

  const { data: outgoingLinks } = useQuery({
    queryKey: ['docLinks', projectId, 'TC', sourceId, 'outgoing'],
    queryFn: () => linksApi.list({ project_id: projectId, source_type: 'TC', source_id: sourceId }),
  })

  const { data: incomingLinks } = useQuery({
    queryKey: ['docLinks', projectId, 'TC', sourceId, 'incoming'],
    queryFn: () => linksApi.list({ project_id: projectId, target_type: 'TC', target_id: sourceId }),
  })

  const deleteMutation = useMutation({
    mutationFn: linksApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docLinks', projectId] })
    },
  })

  const docLookup = useMemo(() => {
    const map = new Map<string, DocShell>()
    ;(docs || []).forEach((doc) => map.set(docKey(doc.doc_type, doc.id), doc))
    return map
  }, [docs])

  const linkCount = (outgoingLinks?.length || 0) + (incomingLinks?.length || 0)

  return (
    <div className="bg-card rounded-lg shadow-elegant">
      <div className="px-6 py-4 border-b border-border flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Document Links</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Typed links from this test case to requirements, specifications, designs, risks, and other controlled documents.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center px-3 py-2 border border-input rounded-md text-sm font-medium hover:bg-accent/50"
        >
          <Link2 className="h-4 w-4 mr-2" />
          Link Document
        </button>
      </div>

      {linkCount === 0 ? (
        <div className="p-6 text-center text-muted-foreground">No document links yet.</div>
      ) : (
        <div className="divide-y divide-border">
          {(outgoingLinks || []).map((link) => (
            <DocumentLinkRow
              key={`out-${link.id}`}
              link={link}
              doc={docLookup.get(docKey(link.target_type, link.target_id))}
              projectPrefix={projectPrefix}
              direction="outgoing"
              onDelete={() => deleteMutation.mutate(link.id)}
            />
          ))}
          {(incomingLinks || []).map((link) => (
            <DocumentLinkRow
              key={`in-${link.id}`}
              link={link}
              doc={docLookup.get(docKey(link.source_type, link.source_id))}
              projectPrefix={projectPrefix}
              direction="incoming"
              onDelete={() => deleteMutation.mutate(link.id)}
            />
          ))}
        </div>
      )}

      {showModal && (
        <LinkDocumentModal
          projectId={projectId}
          sourceId={sourceId}
          docs={(docs || []).filter((doc) => !(doc.doc_type === 'TC' && doc.id === sourceId))}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}

function LinkDocumentModal({
  projectId,
  sourceId,
  docs,
  onClose,
}: {
  projectId: number
  sourceId: number
  docs: DocShell[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [role, setRole] = useState<(typeof LINK_ROLES)[number]>('verifies')
  const [search, setSearch] = useState('')

  const createMutation = useMutation({
    mutationFn: (target: DocShell) => linksApi.create({
      project_id: projectId,
      source_type: 'TC',
      source_id: sourceId,
      target_type: target.doc_type,
      target_id: target.id,
      role,
      suspect: false,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docLinks', projectId] })
      onClose()
    },
  })

  const filteredDocs = docs.filter((doc) => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    return doc.doc_id.toLowerCase().includes(q) || doc.title.toLowerCase().includes(q) || doc.doc_type.toLowerCase().includes(q)
  })

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-card rounded-lg shadow-elegant max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
        <div className="px-6 py-4 border-b border-border flex justify-between items-center">
          <h3 className="text-lg font-semibold">Link Document</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">✕</button>
        </div>
        <div className="p-6 border-b border-border grid grid-cols-1 md:grid-cols-[1fr_12rem] gap-3">
          <div className="relative">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search controlled documents"
              className="w-full pl-9 pr-3 py-2 bg-background border border-input rounded-md text-sm"
            />
          </div>
          <select
            value={role}
            onChange={(event) => setRole(event.target.value as (typeof LINK_ROLES)[number])}
            className="px-3 py-2 bg-background border border-input rounded-md text-sm"
          >
            {LINK_ROLES.map((item) => (
              <option key={item} value={item}>{roleLabel(item, 'outgoing')}</option>
            ))}
          </select>
        </div>
        <div className="overflow-y-auto p-3">
          {filteredDocs.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">No matching documents.</div>
          ) : (
            <div className="divide-y divide-border">
              {filteredDocs.map((doc) => (
                <button
                  key={`${doc.doc_type}-${doc.id}`}
                  onClick={() => createMutation.mutate(doc)}
                  disabled={createMutation.isPending}
                  className="w-full px-3 py-3 text-left hover:bg-accent/50 disabled:opacity-50"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <span className="font-mono text-sm text-primary mr-2">{doc.doc_id}</span>
                      <span className="text-sm font-medium text-foreground">{doc.title}</span>
                    </div>
                    <span className="shrink-0 rounded border border-border px-2 py-0.5 text-[11px] font-semibold text-muted-foreground">
                      {DOC_TYPE_LABELS[doc.doc_type] || doc.doc_type}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function DocumentLinkRow({
  link,
  doc,
  projectPrefix,
  direction,
  onDelete,
}: {
  link: ArtefactLink
  doc: DocShell | undefined
  projectPrefix: string
  direction: 'incoming' | 'outgoing'
  onDelete: () => void
}) {
  return (
    <div className="flex items-center justify-between px-6 py-4 hover:bg-accent/50 transition-colors">
      <Link to={doc ? `/projects/${projectPrefix}/docs/${doc.doc_id}` : '#'} className="min-w-0 flex items-center">
        <FileText className="h-5 w-5 text-primary mr-3 shrink-0" />
        <div className="min-w-0">
          <div>
            <span className="font-mono text-sm text-primary mr-2">{doc?.doc_id || `${direction === 'outgoing' ? link.target_type : link.source_type} #${direction === 'outgoing' ? link.target_id : link.source_id}`}</span>
            <span className="text-foreground">{doc?.title || 'Linked document'}</span>
          </div>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            <span>{direction === 'incoming' ? 'Incoming' : 'Outgoing'}</span>
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-primary">{roleLabel(link.role, direction)}</span>
            {link.suspect && <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-amber-700 dark:text-amber-400">suspect</span>}
            <span>{formatDateTime(link.created_at)} ago</span>
          </div>
        </div>
      </Link>
      <button
        onClick={onDelete}
        className="ml-3 p-1.5 rounded text-muted-foreground hover:text-red-500 hover:bg-red-500/10"
        title="Remove link"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

function MembershipPanel({ title, countLabel, emptyText, children }: { title: string; countLabel: string; emptyText: string; children: ReactNode }) {
  const hasChildren = Array.isArray(children) ? children.length > 0 : Boolean(children)
  return (
    <div className="bg-card rounded-lg shadow-elegant">
      <div className="px-6 py-4 border-b border-border flex justify-between items-center">
        <h3 className="text-lg font-semibold">{title}</h3>
        <span className="text-sm text-muted-foreground">{countLabel}</span>
      </div>
      {hasChildren ? <div className="divide-y divide-border">{children}</div> : <div className="p-6 text-center text-muted-foreground">{emptyText}</div>}
    </div>
  )
}

function docKey(type: string, id: number) {
  return `${type}:${id}`
}

function roleLabel(role: string, direction: 'incoming' | 'outgoing') {
  const labels: Record<string, [string, string]> = {
    verifies: ['verifies', 'verified by'],
    implements: ['implements', 'implemented by'],
    references: ['references', 'referenced by'],
    depends_on: ['depends on', 'dependency of'],
    impacts: ['impacts', 'impacted by'],
    blocks: ['blocks', 'blocked by'],
  }
  const pair = labels[role]
  if (!pair) return role.split('_').join(' ')
  return direction === 'outgoing' ? pair[0] : pair[1]
}

function TcStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Draft: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Active: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Deprecated: 'bg-red-500/10 text-red-700 dark:text-red-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>
      {status}
    </span>
  )
}

function resolveUserName(users: Array<{ id: number; full_name: string }> | undefined, userId: number | null) {
  if (!userId) return 'Unassigned'
  return users?.find((u) => u.id === userId)?.full_name || `User #${userId}`
}
