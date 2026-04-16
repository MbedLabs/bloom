import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { testCasesApi, requirementsApi, usersApi, TcsRow } from '../api/client'
import { TcsArteTable, migrateOldSteps } from '../components/TcsArteTable'
import { ArrowLeft, Pencil, FileText, Link2, X, UserCheck, UserCog, Search } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

function isTcsRow(row: unknown): row is TcsRow {
  return typeof row === 'object' && row !== null && 'row_type' in row
}

function normalizeSteps(steps: unknown): TcsRow[] {
  if (!steps || !Array.isArray(steps) || steps.length === 0) return []
  if (steps.every(isTcsRow)) return steps as TcsRow[]
  return migrateOldSteps(steps as Array<{ step_number: number; action: string; expected_result: string }>)
}

export default function TestCaseDetail() {
  const { itemId } = useParams<{ id: string; itemId: string }>()
  const tcId = parseInt(itemId || '0')
  const queryClient = useQueryClient()

  const { data: testCase, isLoading, error } = useQuery({
    queryKey: ['testCase', tcId],
    queryFn: () => testCasesApi.get(tcId),
    enabled: !!tcId,
  })

  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    title: '',
    description: '',
    preconditions: '',
    status: '',
    reviewer_id: '',
    approver_id: '',
  })
  const [editRows, setEditRows] = useState<TcsRow[]>([])
  const [showLinkModal, setShowLinkModal] = useState(false)
  const [linkType, setLinkType] = useState('verifies')
  const [reqSearch, setReqSearch] = useState('')
  const [linkedReqSearch, setLinkedReqSearch] = useState('')
  const [selectedUnlinkedReqIds, setSelectedUnlinkedReqIds] = useState<number[]>([])
  const [selectedLinkedReqIds, setSelectedLinkedReqIds] = useState<number[]>([])

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })

  const { data: availableRequirements } = useQuery({
    queryKey: ['projectRequirements', testCase?.project_id],
    queryFn: () => requirementsApi.list(testCase!.project_id),
    enabled: !!testCase && showLinkModal,
  })

  useEffect(() => {
    if (testCase && isEditing) {
      setEditForm({
        title: testCase.title,
        description: testCase.description || '',
        preconditions: testCase.preconditions || '',
        status: testCase.status,
        reviewer_id: testCase.reviewer_id ? String(testCase.reviewer_id) : '',
        approver_id: testCase.approver_id ? String(testCase.approver_id) : '',
      })
      setEditRows(normalizeSteps(testCase.steps))
    }
  }, [testCase, isEditing])

  const updateMutation = useMutation({
    mutationFn: (data: Parameters<typeof testCasesApi.update>[1]) => testCasesApi.update(tcId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCase', tcId] })
      setIsEditing(false)
    },
  })

  const linkReqMutation = useMutation({
    mutationFn: (requirementId: number) => testCasesApi.linkRequirement(tcId, requirementId, linkType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCase', tcId] })
      setShowLinkModal(false)
    },
  })

  const unlinkReqMutation = useMutation({
    mutationFn: (requirementId: number) => testCasesApi.unlinkRequirement(tcId, requirementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCase', tcId] })
    },
  })

  const bulkLinkReqMutation = useMutation({
    mutationFn: async (requirementIds: number[]) => {
      await Promise.all(requirementIds.map((requirementId) => testCasesApi.linkRequirement(tcId, requirementId, linkType)))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCase', tcId] })
      setSelectedUnlinkedReqIds([])
    },
  })

  const bulkUnlinkReqMutation = useMutation({
    mutationFn: async (requirementIds: number[]) => {
      await Promise.all(requirementIds.map((requirementId) => testCasesApi.unlinkRequirement(tcId, requirementId)))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCase', tcId] })
      setSelectedLinkedReqIds([])
    },
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

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate({
      title: editForm.title,
      description: editForm.description || null,
      preconditions: editForm.preconditions || null,
      status: editForm.status,
      steps: editRows.length > 0 ? editRows : null,
      reviewer_id: editForm.reviewer_id ? Number(editForm.reviewer_id) : null,
      approver_id: editForm.approver_id ? Number(editForm.approver_id) : null,
    })
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (error || !testCase) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Test Case Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          ← Back to Projects
        </Link>
      </div>
    )
  }

  const tcsRows = normalizeSteps(testCase.steps)
  const linkedReqIds = new Set(testCase.verifies?.map((v) => v.requirement.id) || [])
  const unlinkedRequirements = (availableRequirements || []).filter((req) => !linkedReqIds.has(req.id))
  const filteredUnlinkedRequirements = unlinkedRequirements.filter((req) => {
    const q = reqSearch.trim().toLowerCase()
    if (!q) return true
    return req.req_id.toLowerCase().includes(q) || req.title.toLowerCase().includes(q)
  })
  const filteredLinkedRequirements = (testCase.verifies || []).filter((link) => {
    const q = linkedReqSearch.trim().toLowerCase()
    if (!q) return true
    return link.requirement.req_id.toLowerCase().includes(q) || link.requirement.title.toLowerCase().includes(q)
  })

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${testCase.project_id}`} className="p-2 hover:bg-accent/50 rounded-md">
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
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowLinkModal(true)}
            className="inline-flex items-center px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50 transition-colors text-sm"
          >
            <Link2 className="h-4 w-4 mr-2" />
            Link Requirement
          </button>
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
          >
            <Pencil className="h-4 w-4 mr-2" />
            {isEditing ? 'Cancel Editing' : 'Edit'}
          </button>
        </div>
      </div>

      {isEditing ? (
        <form onSubmit={handleEditSubmit} className="space-y-6">
          <div className="bg-card rounded-lg shadow-elegant p-6 space-y-4">
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
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Preconditions (Text)</label>
              <textarea
                value={editForm.preconditions}
                onChange={(e) => setEditForm({ ...editForm, preconditions: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                rows={2}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Status</label>
              <select
                value={editForm.status}
                onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                className="px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
              >
                <option>Draft</option>
                <option>Active</option>
                <option>Deprecated</option>
              </select>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
          </div>

          <div>
            <h3 className="text-sm font-medium text-foreground mb-2">TCS Artefact Table</h3>
            <TcsArteTable rows={editRows} onChange={setEditRows} editable />
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
      ) : (
        <>
          <div className="bg-card rounded-lg shadow-elegant p-6">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Description</h3>
            <p className="text-foreground whitespace-pre-wrap">
              {testCase.description || 'No description provided.'}
            </p>
          </div>

          {testCase.preconditions && (
            <div className="bg-card rounded-lg shadow-elegant p-6">
              <h3 className="text-sm font-medium text-muted-foreground mb-2">Preconditions</h3>
              <p className="text-foreground whitespace-pre-wrap">{testCase.preconditions}</p>
            </div>
          )}
        </>
      )}

      {!isEditing && tcsRows.length > 0 && (
        <TcsArteTable rows={tcsRows} onChange={() => {}} editable={false} />
      )}

      {!isEditing && (
        <>
          <div className="bg-card rounded-lg shadow-elegant">
            <div className="px-6 py-4 border-b border-border flex justify-between items-center">
              <h3 className="text-lg font-semibold">Verifies Requirements</h3>
              <span className="text-sm text-muted-foreground">{testCase.verifies?.length || 0} verification link{(testCase.verifies?.length || 0) !== 1 ? 's' : ''}</span>
            </div>
            <div className="px-6 py-3 border-b border-border flex flex-col md:flex-row md:items-center gap-3">
              <div className="relative flex-1">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={linkedReqSearch}
                  onChange={(e) => setLinkedReqSearch(e.target.value)}
                  placeholder="Filter linked requirements"
                  className="w-full pl-9 pr-3 py-2 bg-background border border-input rounded-md text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    if (selectedLinkedReqIds.length === filteredLinkedRequirements.length) {
                      setSelectedLinkedReqIds([])
                    } else {
                      setSelectedLinkedReqIds(filteredLinkedRequirements.map((l) => l.requirement.id))
                    }
                  }}
                  className="px-3 py-2 border border-input rounded-md text-xs font-medium hover:bg-accent/50"
                >
                  {selectedLinkedReqIds.length === filteredLinkedRequirements.length && filteredLinkedRequirements.length > 0 ? 'Clear' : 'Select all'}
                </button>
                <button
                  onClick={() => bulkUnlinkReqMutation.mutate(selectedLinkedReqIds)}
                  disabled={selectedLinkedReqIds.length === 0 || bulkUnlinkReqMutation.isPending}
                  className="px-3 py-2 border border-red-500/50 text-red-600 rounded-md text-xs font-medium hover:bg-red-500/10 disabled:opacity-50"
                >
                  {bulkUnlinkReqMutation.isPending ? 'Unlinking...' : `Unlink selected (${selectedLinkedReqIds.length})`}
                </button>
              </div>
            </div>
            {testCase.verifies && testCase.verifies.length > 0 ? (
              <div className="divide-y divide-border">
                {filteredLinkedRequirements.map((link) => (
                  <Link
                    key={link.id}
                    to={`/requirements/${link.requirement.id}`}
                    className="flex items-center justify-between px-6 py-4 hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        checked={selectedLinkedReqIds.includes(link.requirement.id)}
                        onChange={(e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          setSelectedLinkedReqIds((prev) =>
                            prev.includes(link.requirement.id)
                              ? prev.filter((id) => id !== link.requirement.id)
                              : [...prev, link.requirement.id]
                          )
                        }}
                        className="mr-3"
                      />
                      <FileText className="h-5 w-5 text-primary mr-3" />
                      <div>
                        <span className="font-mono text-sm text-primary mr-2">{link.requirement.req_id}</span>
                        <span className="text-foreground">{link.requirement.title}</span>
                        <span className="ml-2 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">{friendlyVerificationLabel(link.link_type, 'outgoing')}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <RequirementStatusBadge status={link.requirement.status} />
                      <div className="text-xs text-muted-foreground mt-1">{formatDistanceToNow(new Date(link.created_at))} ago</div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        unlinkReqMutation.mutate(link.requirement.id)
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
                No requirements linked to this test case.
              </div>
            )}
          </div>

          <div className="bg-card rounded-lg shadow-elegant p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-md border border-border p-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Review</p>
              <p className="text-sm text-foreground">Assigned reviewer: {resolveUserName(users, testCase.reviewer_id)}</p>
              <p className="text-xs text-muted-foreground mt-1">Reviewed by: {resolveUserName(users, testCase.reviewed_by_id)}</p>
              {testCase.reviewed_at && <p className="text-xs text-muted-foreground mt-1">At {new Date(testCase.reviewed_at).toLocaleString()}</p>}
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
              {testCase.approved_at && <p className="text-xs text-muted-foreground mt-1">At {new Date(testCase.approved_at).toLocaleString()}</p>}
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

          <div className="bg-card rounded-lg shadow-elegant">
            <div className="px-6 py-4 border-b border-border flex justify-between items-center">
              <h3 className="text-lg font-semibold">Contained In Suites</h3>
              <span className="text-sm text-muted-foreground">{testCase.suite_memberships?.length || 0} suite{(testCase.suite_memberships?.length || 0) !== 1 ? 's' : ''}</span>
            </div>
            {testCase.suite_memberships && testCase.suite_memberships.length > 0 ? (
              <div className="divide-y divide-border">
                {testCase.suite_memberships.map((suite) => (
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
              <div className="p-6 text-center text-muted-foreground">This test case is not part of any suite yet.</div>
            )}
          </div>

          <div className="bg-card rounded-lg shadow-elegant">
            <div className="px-6 py-4 border-b border-border flex justify-between items-center">
              <h3 className="text-lg font-semibold">Included In Campaign Scopes</h3>
              <span className="text-sm text-muted-foreground">{testCase.campaign_memberships?.length || 0} campaign{(testCase.campaign_memberships?.length || 0) !== 1 ? 's' : ''}</span>
            </div>
            {testCase.campaign_memberships && testCase.campaign_memberships.length > 0 ? (
              <div className="divide-y divide-border">
                {testCase.campaign_memberships.map((campaign) => (
                  <div key={campaign.id} className="px-6 py-4 flex items-center justify-between">
                    <div className="text-foreground">{campaign.name}</div>
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{campaign.status}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center text-muted-foreground">This test case is not included in any campaign scope yet.</div>
            )}
          </div>

          <div className="text-sm text-muted-foreground flex items-center space-x-6">
            <span>Created {formatDistanceToNow(new Date(testCase.created_at))} ago</span>
            <span>Updated {formatDistanceToNow(new Date(testCase.updated_at))} ago</span>
          </div>
        </>
      )}

      {showLinkModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-elegant max-w-lg w-full mx-4 max-h-[80vh] flex flex-col">
            <div className="px-6 py-4 border-b border-border flex justify-between items-center">
              <h3 className="text-lg font-semibold">Link Requirement</h3>
              <button onClick={() => setShowLinkModal(false)} className="text-muted-foreground hover:text-foreground">✕</button>
            </div>
            <div className="overflow-y-auto p-6">
              <div className="mb-4 relative">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={reqSearch}
                  onChange={(e) => setReqSearch(e.target.value)}
                  placeholder="Filter available requirements"
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
                  <option value="validates">validates</option>
                </select>
              </div>
              <div className="mb-4 flex items-center gap-2">
                <button
                  onClick={() => {
                    if (selectedUnlinkedReqIds.length === filteredUnlinkedRequirements.length) {
                      setSelectedUnlinkedReqIds([])
                    } else {
                      setSelectedUnlinkedReqIds(filteredUnlinkedRequirements.map((req) => req.id))
                    }
                  }}
                  className="px-3 py-2 border border-input rounded-md text-xs font-medium hover:bg-accent/50"
                >
                  {selectedUnlinkedReqIds.length === filteredUnlinkedRequirements.length && filteredUnlinkedRequirements.length > 0 ? 'Clear' : 'Select all'}
                </button>
                <button
                  onClick={() => bulkLinkReqMutation.mutate(selectedUnlinkedReqIds)}
                  disabled={selectedUnlinkedReqIds.length === 0 || bulkLinkReqMutation.isPending}
                  className="px-3 py-2 bg-primary text-primary-foreground rounded-md text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
                >
                  {bulkLinkReqMutation.isPending ? 'Linking...' : `Link selected (${selectedUnlinkedReqIds.length})`}
                </button>
              </div>
              {filteredUnlinkedRequirements.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">No matching requirements available.</div>
              ) : (
                <div className="space-y-2">
                  {filteredUnlinkedRequirements.map((req) => (
                    <div
                      key={req.id}
                      onClick={() => {
                        setSelectedUnlinkedReqIds((prev) =>
                          prev.includes(req.id) ? prev.filter((id) => id !== req.id) : [...prev, req.id]
                        )
                      }}
                      className="w-full flex items-center justify-between px-4 py-3 rounded-md border border-border hover:border-primary/50 hover:bg-primary/10 transition-colors text-left disabled:opacity-50"
                    >
                      <div>
                        <input
                          type="checkbox"
                          checked={selectedUnlinkedReqIds.includes(req.id)}
                          readOnly
                          className="mr-3"
                        />
                        <span className="font-mono text-sm text-primary mr-2">{req.req_id}</span>
                        <span className="text-foreground">{req.title}</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          linkReqMutation.mutate(req.id)
                        }}
                        disabled={linkReqMutation.isPending}
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

function friendlyVerificationLabel(linkType: string, direction: 'incoming' | 'outgoing') {
  if (linkType === 'verifies') return direction === 'incoming' ? 'verified by' : 'verifies'
  if (linkType === 'validates') return direction === 'incoming' ? 'validated by' : 'validates'
  return linkType.split('_').join(' ')
}

function resolveUserName(users: Array<{ id: number; full_name: string }> | undefined, userId: number | null) {
  if (!userId) return 'Unassigned'
  return users?.find((u) => u.id === userId)?.full_name || `User #${userId}`
}
