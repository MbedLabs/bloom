import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { requirementsApi, testCasesApi, usersApi, projectsApi } from '../api/client'
import { ArrowLeft, Pencil, Link2, ExternalLink, ChevronRight, CheckCircle, UserCheck, UserCog, X, Search } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function RequirementDetail({ resolvedId }: { resolvedId?: number } = {}) {
  const { itemId } = useParams<{ prefix: string; itemId: string }>()
  const reqId = resolvedId || parseInt(itemId || '0')
  const queryClient = useQueryClient()

  const { data: requirement, isLoading, error } = useQuery({
    queryKey: ['requirement', reqId],
    queryFn: () => requirementsApi.get(reqId),
    enabled: !!reqId,
  })

  const { data: project } = useQuery({
    queryKey: ['project', requirement?.project_id],
    queryFn: () => projectsApi.get(requirement!.project_id),
    enabled: !!requirement?.project_id,
  })

  const projectPrefix = project?.prefix || ''

  const { data: parentReq } = useQuery({
    queryKey: ['requirement', requirement?.parent_id],
    queryFn: () => requirementsApi.get(requirement!.parent_id!),
    enabled: !!requirement?.parent_id,
  })

  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    title: '',
    description: '',
    status: '',
    priority: '',
    req_type: '',
    req_origin: '',
    reviewer_id: '',
    approver_id: '',
  })
  const [showLinkModal, setShowLinkModal] = useState(false)
  const [linkType, setLinkType] = useState('verifies')
  const [tcSearch, setTcSearch] = useState('')
  const [linkedTcSearch, setLinkedTcSearch] = useState('')
  const [selectedUnlinkedTcIds, setSelectedUnlinkedTcIds] = useState<number[]>([])
  const [selectedLinkedTcIds, setSelectedLinkedTcIds] = useState<number[]>([])

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })

  const { data: availableTestCases } = useQuery({
    queryKey: ['projectTestCases', requirement?.project_id],
    queryFn: () => testCasesApi.list(requirement!.project_id),
    enabled: !!requirement && showLinkModal,
  })

  useEffect(() => {
    if (requirement && isEditing) {
      setEditForm({
        title: requirement.title,
        description: requirement.description || '',
        status: requirement.status,
        priority: requirement.priority,
        req_type: requirement.req_type,
        req_origin: requirement.req_origin,
        reviewer_id: requirement.reviewer_id ? String(requirement.reviewer_id) : '',
        approver_id: requirement.approver_id ? String(requirement.approver_id) : '',
      })
    }
  }, [requirement, isEditing])

  const updateMutation = useMutation({
    mutationFn: (data: Parameters<typeof requirementsApi.update>[1]) => requirementsApi.update(reqId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirement', reqId] })
      setIsEditing(false)
    },
  })

  const linkTcMutation = useMutation({
    mutationFn: (testCaseId: number) => requirementsApi.linkTestCase(reqId, testCaseId, linkType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirement', reqId] })
      setShowLinkModal(false)
    },
  })

  const unlinkTcMutation = useMutation({
    mutationFn: (testCaseId: number) => requirementsApi.unlinkTestCase(reqId, testCaseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirement', reqId] })
    },
  })

  const bulkLinkTcMutation = useMutation({
    mutationFn: async (testCaseIds: number[]) => {
      await Promise.all(testCaseIds.map((testCaseId) => requirementsApi.linkTestCase(reqId, testCaseId, linkType)))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirement', reqId] })
      setSelectedUnlinkedTcIds([])
    },
  })

  const bulkUnlinkTcMutation = useMutation({
    mutationFn: async (testCaseIds: number[]) => {
      await Promise.all(testCaseIds.map((testCaseId) => requirementsApi.unlinkTestCase(reqId, testCaseId)))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirement', reqId] })
      setSelectedLinkedTcIds([])
    },
  })

  const markReviewedMutation = useMutation({
    mutationFn: (reviewedById: number) => requirementsApi.setReviewed(reqId, reviewedById),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirement', reqId] })
    },
  })

  const markApprovedMutation = useMutation({
    mutationFn: (approvedById: number) => requirementsApi.setApproved(reqId, approvedById),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirement', reqId] })
    },
  })

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate({
      title: editForm.title,
      description: editForm.description || null,
      status: editForm.status,
      priority: editForm.priority,
      req_type: editForm.req_type,
      req_origin: editForm.req_origin,
      reviewer_id: editForm.reviewer_id ? Number(editForm.reviewer_id) : null,
      approver_id: editForm.approver_id ? Number(editForm.approver_id) : null,
    })
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (error || !requirement) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Requirement Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          ← Back to Projects
        </Link>
      </div>
    )
  }

  const linkedTcIds = new Set(requirement.linked_test_cases?.map(tc => tc.id) || [])
  const unlinkedTestCases = availableTestCases?.filter(tc => !linkedTcIds.has(tc.id)) || []
  const filteredUnlinkedTestCases = unlinkedTestCases.filter((tc) => {
    const q = tcSearch.trim().toLowerCase()
    if (!q) return true
    return tc.tc_id.toLowerCase().includes(q) || tc.title.toLowerCase().includes(q)
  })
  const filteredLinkedTestCases = (requirement.verified_by || []).filter((link) => {
    const q = linkedTcSearch.trim().toLowerCase()
    if (!q) return true
    return link.test_case.tc_id.toLowerCase().includes(q) || link.test_case.title.toLowerCase().includes(q)
  })

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${projectPrefix}`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <div className="flex items-center space-x-3">
              <span className="font-mono text-sm text-primary font-semibold">{requirement.req_id}</span>
              <RequirementStatusBadge status={requirement.status} />
              <PriorityBadge priority={requirement.priority} />
              <TypeBadge reqType={requirement.req_type} />
              <OriginBadge origin={requirement.req_origin} />
            </div>
            <h2 className="text-2xl font-bold text-foreground mt-1">{requirement.title}</h2>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowLinkModal(true)}
            className="inline-flex items-center px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50 transition-colors text-sm"
          >
            <Link2 className="h-4 w-4 mr-2" />
            Link Test Case
          </button>
          <button
            onClick={() => setIsEditing(true)}
            className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
          >
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </button>
        </div>
      </div>

      {requirement.parent_id && parentReq && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <span className="text-sm text-blue-600 font-medium">Parent Requirement: </span>
          <Link to={`/projects/${projectPrefix}/docs/${parentReq.req_id}`} className="text-sm text-primary hover:text-primary/80 font-medium">
            {parentReq.req_id} — {parentReq.title} →
          </Link>
        </div>
      )}

      {isEditing ? (
        <div className="bg-card rounded-lg shadow-elegant p-6">
          <form onSubmit={handleEditSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Title</label>
              <input
                type="text"
                required
                value={editForm.title}
                onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Description</label>
              <textarea
                value={editForm.description}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                rows={4}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Status</label>
                <select
                  value={editForm.status}
                  onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                >
                  <option>Draft</option>
                  <option>Review</option>
                  <option>Approved</option>
                  <option>Implemented</option>
                  <option>Verified</option>
                  <option>Rejected</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Priority</label>
                <select
                  value={editForm.priority}
                  onChange={(e) => setEditForm({ ...editForm, priority: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                >
                  <option>Low</option>
                  <option>Medium</option>
                  <option>High</option>
                  <option>Critical</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Type</label>
                <select
                  value={editForm.req_type}
                  onChange={(e) => setEditForm({ ...editForm, req_type: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                >
                  <option>Functional</option>
                  <option>Non-Functional</option>
                  <option>Performance</option>
                  <option>Security</option>
                  <option>Usability</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Origin</label>
                <select
                  value={editForm.req_origin}
                  onChange={(e) => setEditForm({ ...editForm, req_origin: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                >
                  <option>Internal</option>
                  <option>Customer</option>
                  <option>Compliance</option>
                  <option>Regulatory</option>
                  <option>Legal</option>
                  <option>Business</option>
                  <option>Technical</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Reviewer</label>
                <select
                  value={editForm.reviewer_id}
                  onChange={(e) => setEditForm({ ...editForm, reviewer_id: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                >
                  <option value="">Unassigned</option>
                  {(users || []).map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Approver</label>
                <select
                  value={editForm.approver_id}
                  onChange={(e) => setEditForm({ ...editForm, approver_id: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                >
                  <option value="">Unassigned</option>
                  {(users || []).map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={updateMutation.isPending}
                className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
              >
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="bg-card rounded-lg shadow-elegant p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Description</h3>
          <p className="text-foreground whitespace-pre-wrap">
            {requirement.description || 'No description provided.'}
          </p>
          <div className="mt-4 pt-4 border-t border-border flex items-center space-x-6 text-sm text-muted-foreground">
            <span>Created {formatDistanceToNow(new Date(requirement.created_at))} ago</span>
            <span>Updated {formatDistanceToNow(new Date(requirement.updated_at))} ago</span>
          </div>
          <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-md border border-border p-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Review</p>
              <p className="text-sm text-foreground">Assigned reviewer: {resolveUserName(users, requirement.reviewer_id)}</p>
              <p className="text-xs text-muted-foreground mt-1">Reviewed by: {resolveUserName(users, requirement.reviewed_by_id)}</p>
              {requirement.reviewed_at && (
                <p className="text-xs text-muted-foreground mt-1">At {new Date(requirement.reviewed_at).toLocaleString()}</p>
              )}
              <button
                disabled={!requirement.reviewer_id || markReviewedMutation.isPending}
                onClick={() => requirement.reviewer_id && markReviewedMutation.mutate(requirement.reviewer_id)}
                className="mt-3 inline-flex items-center px-3 py-1.5 rounded-md bg-amber-500/90 text-white text-xs font-medium hover:bg-amber-500 disabled:opacity-50"
              >
                <UserCheck className="h-3.5 w-3.5 mr-1" />
                Mark Reviewed
              </button>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Approval</p>
              <p className="text-sm text-foreground">Assigned approver: {resolveUserName(users, requirement.approver_id)}</p>
              <p className="text-xs text-muted-foreground mt-1">Approved by: {resolveUserName(users, requirement.approved_by_id)}</p>
              {requirement.approved_at && (
                <p className="text-xs text-muted-foreground mt-1">At {new Date(requirement.approved_at).toLocaleString()}</p>
              )}
              <button
                disabled={!requirement.approver_id || markApprovedMutation.isPending}
                onClick={() => requirement.approver_id && markApprovedMutation.mutate(requirement.approver_id)}
                className="mt-3 inline-flex items-center px-3 py-1.5 rounded-md bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-500 disabled:opacity-50"
              >
                <UserCog className="h-3.5 w-3.5 mr-1" />
                Mark Approved
              </button>
            </div>
          </div>
        </div>
      )}

      {requirement.children && requirement.children.length > 0 && (
        <div className="bg-card rounded-lg shadow-elegant">
          <div className="px-6 py-4 border-b border-border">
            <h3 className="text-lg font-semibold">Child Requirements</h3>
          </div>
          <div className="divide-y divide-border">
            {requirement.children.map((child) => (
              <Link
                key={child.id}
                to={`/projects/${projectPrefix}/docs/${child.req_id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center">
                  <ChevronRight className="h-4 w-4 text-muted-foreground mr-3" />
                  <div>
                    <span className="font-mono text-sm text-primary mr-2">{child.req_id}</span>
                    <span className="text-foreground">{child.title}</span>
                  </div>
                </div>
                <RequirementStatusBadge status={child.status} />
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="bg-card rounded-lg shadow-elegant">
        <div className="px-6 py-4 border-b border-border flex justify-between items-center">
          <h3 className="text-lg font-semibold">Verified By</h3>
          <span className="text-sm text-muted-foreground">{requirement.verified_by?.length || 0} verification link{(requirement.verified_by?.length || 0) !== 1 ? 's' : ''}</span>
        </div>
        <div className="px-6 py-3 border-b border-border flex flex-col md:flex-row md:items-center gap-3">
          <div className="relative flex-1">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              value={linkedTcSearch}
              onChange={(e) => setLinkedTcSearch(e.target.value)}
              placeholder="Filter linked test cases"
              className="w-full pl-9 pr-3 py-2 bg-background border border-input rounded-md text-sm"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (selectedLinkedTcIds.length === filteredLinkedTestCases.length) {
                  setSelectedLinkedTcIds([])
                } else {
                  setSelectedLinkedTcIds(filteredLinkedTestCases.map((l) => l.test_case.id))
                }
              }}
              className="px-3 py-2 border border-input rounded-md text-xs font-medium hover:bg-accent/50"
            >
              {selectedLinkedTcIds.length === filteredLinkedTestCases.length && filteredLinkedTestCases.length > 0 ? 'Clear' : 'Select all'}
            </button>
            <button
              onClick={() => bulkUnlinkTcMutation.mutate(selectedLinkedTcIds)}
              disabled={selectedLinkedTcIds.length === 0 || bulkUnlinkTcMutation.isPending}
              className="px-3 py-2 border border-red-500/50 text-red-600 rounded-md text-xs font-medium hover:bg-red-500/10 disabled:opacity-50"
            >
              {bulkUnlinkTcMutation.isPending ? 'Unlinking...' : `Unlink selected (${selectedLinkedTcIds.length})`}
            </button>
          </div>
        </div>
        {requirement.verified_by && requirement.verified_by.length > 0 ? (
          <div className="divide-y divide-border">
            {filteredLinkedTestCases.map((link) => (
              <Link
                key={link.id}
                to={`/projects/${projectPrefix}/docs/${link.test_case.tc_id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedLinkedTcIds.includes(link.test_case.id)}
                    onChange={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      setSelectedLinkedTcIds((prev) =>
                        prev.includes(link.test_case.id)
                          ? prev.filter((id) => id !== link.test_case.id)
                          : [...prev, link.test_case.id]
                      )
                    }}
                    className="mr-3"
                  />
                  <CheckCircle className="h-5 w-5 text-primary mr-3" />
                  <div>
                    <span className="font-mono text-sm text-primary mr-2">{link.test_case.tc_id}</span>
                    <span className="text-foreground">{link.test_case.title}</span>
                    <span className="ml-2 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">{friendlyVerificationLabel(link.link_type, 'incoming')}</span>
                  </div>
                </div>
                <div className="text-right">
                  <TcStatusBadge status={link.test_case.status} />
                  <div className="text-xs text-muted-foreground mt-1">{formatDistanceToNow(new Date(link.created_at))} ago</div>
                </div>
                <button
                  onClick={(e) => {
                    e.preventDefault()
                    unlinkTcMutation.mutate(link.test_case.id)
                  }}
                  className="ml-3 p-1.5 rounded text-muted-foreground hover:text-red-500 hover:bg-red-500/10"
                  title="Unlink"
                >
                  <X className="h-4 w-4" />
                </button>
              </Link>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center text-muted-foreground">
            No test cases linked yet.
          </div>
        )}
      </div>

      {requirement.linked_test_runs && requirement.linked_test_runs.length > 0 && (
        <div className="bg-card rounded-lg shadow-elegant">
          <div className="px-6 py-4 border-b border-border">
            <h3 className="text-lg font-semibold">Linked Test Runs</h3>
          </div>
          <div className="overflow-hidden">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Test Run</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Link</th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {requirement.linked_test_runs.map((tr) => (
                  <tr key={tr.id} className="hover:bg-accent/50">
                    <td className="px-6 py-4 text-sm font-medium text-foreground">
                      {tr.test_run_name || `Test Run #${tr.test_run_id}`}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {tr.status ? <RunStatusBadge status={tr.status} /> : '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-muted-foreground">
                      {formatDistanceToNow(new Date(tr.created_at))} ago
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {tr.teststation_url ? (
                        <a
                          href={tr.teststation_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center text-primary hover:text-primary/80"
                        >
                          <ExternalLink className="h-4 w-4 mr-1" />
                          Open
                        </a>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-lg shadow-elegant">
          <div className="px-6 py-4 border-b border-border flex justify-between items-center">
            <h3 className="text-lg font-semibold">Appears In Suites</h3>
            <span className="text-sm text-muted-foreground">{requirement.suite_backlinks?.length || 0}</span>
          </div>
          {requirement.suite_backlinks && requirement.suite_backlinks.length > 0 ? (
            <div className="divide-y divide-border">
              {requirement.suite_backlinks.map((suite) => (
                <div key={suite.id} className="px-6 py-4 flex items-center justify-between">
                  <div>
                    <div className="font-mono text-sm text-primary">{suite.suite_id}</div>
                    <div className="text-foreground mt-1">{suite.name}</div>
                  </div>
                  <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{suite.status}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6 text-center text-muted-foreground">No suites include verification test cases for this requirement.</div>
          )}
        </div>

        <div className="bg-card rounded-lg shadow-elegant">
          <div className="px-6 py-4 border-b border-border flex justify-between items-center">
            <h3 className="text-lg font-semibold">Covered By Campaign Scopes</h3>
            <span className="text-sm text-muted-foreground">{requirement.campaign_backlinks?.length || 0}</span>
          </div>
          {requirement.campaign_backlinks && requirement.campaign_backlinks.length > 0 ? (
            <div className="divide-y divide-border">
              {requirement.campaign_backlinks.map((campaign) => (
                <div key={campaign.id} className="px-6 py-4 flex items-center justify-between">
                  <div className="text-foreground">{campaign.name}</div>
                  <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{campaign.status}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6 text-center text-muted-foreground">No campaign scopes reference this requirement yet.</div>
          )}
        </div>
      </div>

      {showLinkModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-elegant max-w-lg w-full mx-4 max-h-[80vh] flex flex-col">
            <div className="px-6 py-4 border-b border-border flex justify-between items-center">
              <h3 className="text-lg font-semibold">Link Test Case</h3>
              <button onClick={() => setShowLinkModal(false)} className="text-muted-foreground hover:text-foreground">
                ✕
              </button>
            </div>
            <div className="overflow-y-auto p-6">
              <div className="mb-4 relative">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={tcSearch}
                  onChange={(e) => setTcSearch(e.target.value)}
                  placeholder="Filter available test cases"
                  className="w-full pl-9 pr-3 py-2 bg-background border border-input rounded-md text-sm"
                />
              </div>
              <div className="mb-4">
                <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Link Type</label>
                <select
                  value={linkType}
                  onChange={(e) => setLinkType(e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground"
                >
                  <option value="verifies">verifies</option>
                </select>
              </div>
              <div className="mb-4 flex items-center gap-2">
                <button
                  onClick={() => {
                    if (selectedUnlinkedTcIds.length === filteredUnlinkedTestCases.length) {
                      setSelectedUnlinkedTcIds([])
                    } else {
                      setSelectedUnlinkedTcIds(filteredUnlinkedTestCases.map((tc) => tc.id))
                    }
                  }}
                  className="px-3 py-2 border border-input rounded-md text-xs font-medium hover:bg-accent/50"
                >
                  {selectedUnlinkedTcIds.length === filteredUnlinkedTestCases.length && filteredUnlinkedTestCases.length > 0 ? 'Clear' : 'Select all'}
                </button>
                <button
                  onClick={() => bulkLinkTcMutation.mutate(selectedUnlinkedTcIds)}
                  disabled={selectedUnlinkedTcIds.length === 0 || bulkLinkTcMutation.isPending}
                  className="px-3 py-2 bg-primary text-primary-foreground rounded-md text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
                >
                  {bulkLinkTcMutation.isPending ? 'Linking...' : `Link selected (${selectedUnlinkedTcIds.length})`}
                </button>
              </div>
              {filteredUnlinkedTestCases.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  <CheckCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p>No matching test cases available.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredUnlinkedTestCases.map((tc) => (
                    <div
                      key={tc.id}
                      onClick={() => {
                        setSelectedUnlinkedTcIds((prev) =>
                          prev.includes(tc.id) ? prev.filter((id) => id !== tc.id) : [...prev, tc.id]
                        )
                      }}
                      className="w-full flex items-center justify-between px-4 py-3 rounded-md border border-border hover:border-primary/50 hover:bg-primary/10 transition-colors text-left disabled:opacity-50"
                    >
                      <div>
                        <input
                          type="checkbox"
                          checked={selectedUnlinkedTcIds.includes(tc.id)}
                          readOnly
                          className="mr-3"
                        />
                        <span className="font-mono text-sm text-primary mr-2">{tc.tc_id}</span>
                        <span className="text-foreground">{tc.title}</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          linkTcMutation.mutate(tc.id)
                        }}
                        disabled={linkTcMutation.isPending}
                        className="px-2 py-1 border border-input rounded text-xs hover:bg-accent/50"
                      >
                        Link
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function RequirementStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Draft: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Review: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Approved: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Implemented: 'bg-teal-500/10 text-teal-700 dark:text-teal-400',
    Verified: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Rejected: 'bg-red-500/10 text-red-700 dark:text-red-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>
      {status}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    Low: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Medium: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    High: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
    Critical: 'bg-red-500/10 text-red-700 dark:text-red-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[priority] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>
      {priority}
    </span>
  )
}

function TypeBadge({ reqType }: { reqType: string }) {
  return (
    <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-700 dark:text-purple-400">
      {reqType}
    </span>
  )
}

function OriginBadge({ origin }: { origin: string }) {
  const colors: Record<string, string> = {
    Internal: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
    Customer: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400',
    Compliance: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
    Regulatory: 'bg-rose-500/10 text-rose-700 dark:text-rose-400',
    Legal: 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400',
    Business: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Technical: 'bg-teal-500/10 text-teal-700 dark:text-teal-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[origin] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>
      {origin}
    </span>
  )
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

function RunStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Passed: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Failed: 'bg-red-500/10 text-red-700 dark:text-red-400',
    Running: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Pending: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>
      {status}
    </span>
  )
}

function friendlyVerificationLabel(linkType: string, direction: 'incoming' | 'outgoing') {
  if (linkType === 'verifies') return direction === 'incoming' ? 'verified by' : 'verifies'
  return linkType.split('_').join(' ')
}

function resolveUserName(users: Array<{ id: number; full_name: string }> | undefined, userId: number | null) {
  if (!userId) return 'Unassigned'
  return users?.find((u) => u.id === userId)?.full_name || `User #${userId}`
}
