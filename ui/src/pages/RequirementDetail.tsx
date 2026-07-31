import { useState, useEffect, useMemo } from 'react'
import { useParams, Link, useNavigate } from 'react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { requirementsApi, usersApi, projectsApi, extractApiErrorMessage } from '../api/client'
import { ExternalLink, ChevronRight, UserCheck, UserCog, Trash2 } from 'lucide-react'
import { formatDateTime } from '../test/date-utils'
import { docUrl } from '../types/doc'
import { docRegistryListUrl } from '../lib/docRegistryParams'
import DocumentActivityPanel from '../components/DocumentActivityPanel'
import DocDetailShell, { StatusBadge, MetaItem, SectionCard } from '../components/DocDetailShell'
import { DocumentLinksPanel } from '../components/DocumentLinksPanel'
import { useAuth } from '../contexts/AuthContext'
import {
  membershipLinksForCampaigns,
  membershipLinksForSuites,
} from '../lib/membershipLinks'

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
    Customer: 'bg-sky-500/10 text-sky-700 dark:text-sky-400',
    Compliance: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
    Regulatory: 'bg-rose-500/10 text-rose-700 dark:text-rose-400',
    Legal: 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400',
    Business: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Technical: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[origin] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>
      {origin}
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

function resolveUserName(users: Array<{ id: number; full_name: string }> | undefined, userId: number | null) {
  if (!userId) return 'Unassigned'
  return users?.find((u) => u.id === userId)?.full_name || `User #${userId}`
}

export default function RequirementDetail({ resolvedId }: { resolvedId?: number } = {}) {
  const { user } = useAuth()
  const { prefix, itemId } = useParams<{ prefix: string; itemId: string }>()
  const reqId = resolvedId || parseInt(itemId || '0')
  const queryClient = useQueryClient()
  const navigate = useNavigate()

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

  const derivedMembershipLinks = useMemo(() => {
    if (!requirement) return []
    return [
      ...membershipLinksForSuites(
        requirement.suite_backlinks,
        'REQ',
        requirement.id,
        requirement.project_id,
      ),
      ...membershipLinksForCampaigns(
        requirement.campaign_backlinks,
        'REQ',
        requirement.id,
        requirement.project_id,
      ),
    ]
  }, [requirement])

  const { data: parentReq } = useQuery({
    queryKey: ['requirement', requirement?.parent_id],
    queryFn: () => requirementsApi.get(requirement!.parent_id!),
    enabled: !!requirement?.parent_id,
  })

  const [toast, setToast] = useState<{ message: string; variant: 'success' | 'error' | 'info' } | null>(null)

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(timer)
  }, [toast])

  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    title: '',
    description: '',
    status: '',
    visibility: 'internal',
    priority: '',
    req_type: '',
    req_origin: '',
    reviewer_id: '',
    approver_id: '',
  })

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
    enabled: user?.role === 'admin' || user?.role === 'maintainer',
  })

  useEffect(() => {
    if (requirement && isEditing) {
      setEditForm({
        title: requirement.title,
        description: requirement.description || '',
        status: requirement.status,
        visibility: requirement.visibility,
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
    onSuccess: (updated) => {
      queryClient.setQueryData(['requirement', reqId], (old: unknown) => {
        if (old && typeof old === 'object') {
          return { ...(old as object), ...(updated as object) }
        }
        return updated
      })
      queryClient.invalidateQueries({ queryKey: ['requirement', reqId] })
      queryClient.invalidateQueries({ queryKey: ['artefactActivity', 'requirement', reqId] })
      setIsEditing(false)
      setToast({ message: 'Requirement saved', variant: 'success' })
    },
    onError: (err: unknown) => {
      setToast({ message: extractApiErrorMessage(err) || 'Save failed', variant: 'error' })
    },
  })

  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const deleteMutation = useMutation({
    mutationFn: () => requirementsApi.delete(reqId),
    onSuccess: () => {
      if (!requirement) return
      queryClient.invalidateQueries({ queryKey: ['requirements', requirement.project_id] })
      queryClient.invalidateQueries({ queryKey: ['all-docs', prefix] })
      queryClient.invalidateQueries({ queryKey: ['project', requirement.project_id] })
      queryClient.invalidateQueries({ queryKey: ['artefactActivity', 'requirement', reqId] })
      setToast({ message: 'Requirement deleted', variant: 'success' })
      setTimeout(() => {
        navigate(docRegistryListUrl(prefix!, 'REQ'))
      }, 800)
    },
    onError: (err: unknown) => {
      setToast({ message: extractApiErrorMessage(err) || 'Delete failed', variant: 'error' })
      setDeleteConfirm(false)
    },
  })

  const markReviewedMutation = useMutation({
    mutationFn: (reviewedById: number) => requirementsApi.setReviewed(reqId, reviewedById),
    onSuccess: (updated) => {
      queryClient.setQueryData(['requirement', reqId], (old: unknown) => {
        if (old && typeof old === 'object') {
          return { ...(old as object), ...(updated as object) }
        }
        return updated
      })
      queryClient.invalidateQueries({ queryKey: ['requirement', reqId] })
      queryClient.invalidateQueries({ queryKey: ['artefactActivity', 'requirement', reqId] })
      setToast({ message: 'Requirement marked as reviewed', variant: 'success' })
    },
    onError: (err: unknown) => {
      setToast({ message: extractApiErrorMessage(err) || 'Review failed', variant: 'error' })
    },
  })

  const markApprovedMutation = useMutation({
    mutationFn: (approvedById: number) => requirementsApi.setApproved(reqId, approvedById),
    onSuccess: (updated) => {
      queryClient.setQueryData(['requirement', reqId], (old: unknown) => {
        if (old && typeof old === 'object') {
          return { ...(old as object), ...(updated as object) }
        }
        return updated
      })
      queryClient.invalidateQueries({ queryKey: ['requirement', reqId] })
      queryClient.invalidateQueries({ queryKey: ['artefactActivity', 'requirement', reqId] })
      setToast({ message: 'Requirement approved', variant: 'success' })
    },
    onError: (err: unknown) => {
      setToast({ message: extractApiErrorMessage(err) || 'Approval failed', variant: 'error' })
    },
  })

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate({
      title: editForm.title,
      description: editForm.description || null,
      status: editForm.status,
      visibility: editForm.req_origin === 'Customer' ? 'customer' : 'internal',
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
        <Link to={docRegistryListUrl(prefix!, 'REQ')} className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Requirements
        </Link>
      </div>
    )
  }

  const canEditDocs = user?.role === 'admin' || user?.role === 'maintainer'

  return (
    <>
    <DocDetailShell
      projectPrefix={projectPrefix}
      docType="REQ"
      docCode={requirement.req_id}
      title={requirement.title}
      status={requirement.status}
      priority={requirement.priority}
      actions={canEditDocs ? (
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsEditing(true)}
            className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
          >
            Edit
          </button>
          {!deleteConfirm ? (
            <button
              type="button"
              onClick={() => setDeleteConfirm(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 border border-red-300 text-red-600 rounded-md hover:bg-red-50 text-sm"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Are you sure?</span>
              <button
                onClick={() => { setDeleteConfirm(false); deleteMutation.mutate(); }}
                disabled={deleteMutation.isPending}
                className="inline-flex items-center px-3 py-1.5 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
              <button onClick={() => setDeleteConfirm(false)} className="px-3 py-1.5 border border-input rounded-md text-sm hover:bg-accent/40">
                Cancel
              </button>
            </div>
          )}
        </div>
      ) : undefined}
      rightRail={
        <>
          <SectionCard title="Metadata">
            <div className="space-y-4">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Type</div>
                <TypeBadge reqType={requirement.req_type} />
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Origin</div>
                <OriginBadge origin={requirement.req_origin} />
              </div>
              <MetaItem label="Created" value={formatDateTime(requirement.created_at) + ' ago'} />
              <MetaItem label="Updated" value={formatDateTime(requirement.updated_at) + ' ago'} />
            </div>
          </SectionCard>

          <SectionCard title="Review">
            <div className="space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Reviewer</div>
                <div className="text-sm text-foreground">{resolveUserName(users, requirement.reviewer_id)}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Reviewed by</div>
                <div className="text-sm text-foreground">{resolveUserName(users, requirement.reviewed_by_id)}</div>
                {requirement.reviewed_at && <div className="text-xs text-muted-foreground mt-0.5">{formatDateTime(requirement.reviewed_at)}</div>}
              </div>
              <button
                disabled={!canEditDocs || !requirement.reviewer_id || markReviewedMutation.isPending}
                onClick={() => requirement.reviewer_id && markReviewedMutation.mutate(requirement.reviewer_id)}
                className="w-full inline-flex items-center justify-center px-3 py-1.5 rounded-md bg-amber-500/90 text-white text-xs font-medium hover:bg-amber-500 disabled:opacity-50"
              >
                <UserCheck className="h-3.5 w-3.5 mr-1" />
                Mark Reviewed
              </button>
            </div>
          </SectionCard>

          <SectionCard title="Approval">
            <div className="space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Approver</div>
                <div className="text-sm text-foreground">{resolveUserName(users, requirement.approver_id)}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Approved by</div>
                <div className="text-sm text-foreground">{resolveUserName(users, requirement.approved_by_id)}</div>
                {requirement.approved_at && <div className="text-xs text-muted-foreground mt-0.5">{formatDateTime(requirement.approved_at)}</div>}
              </div>
              <button
                disabled={!canEditDocs || !requirement.approver_id || markApprovedMutation.isPending}
                onClick={() => requirement.approver_id && markApprovedMutation.mutate(requirement.approver_id)}
                className="w-full inline-flex items-center justify-center px-3 py-1.5 rounded-md bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-500 disabled:opacity-50"
              >
                <UserCog className="h-3.5 w-3.5 mr-1" />
                Mark Approved
              </button>
            </div>
          </SectionCard>
        </>
      }
    >
      {requirement.parent_id && parentReq && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <span className="text-sm text-blue-600 font-medium">Parent Requirement: </span>
          <Link to={docUrl(projectPrefix, 'REQ', parentReq.req_id)} className="text-sm text-primary hover:text-primary/80 font-medium">
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
        <SectionCard title="Description">
          <p className="text-foreground whitespace-pre-wrap">
            {requirement.description || 'No description provided.'}
          </p>
        </SectionCard>
      )}

      {requirement.children && requirement.children.length > 0 && (
        <SectionCard title="Child Requirements" actions={<span className="text-sm text-muted-foreground">{requirement.children.length}</span>}>
          <div className="divide-y divide-border -m-6">
            {requirement.children.map((child) => (
              <Link
                key={child.id}
                to={docUrl(projectPrefix, 'REQ', child.req_id)}
                className="flex items-center justify-between px-6 py-4 hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center">
                  <ChevronRight className="h-4 w-4 text-muted-foreground mr-3" />
                  <div>
                    <span className="font-mono text-sm text-primary mr-2">{child.req_id}</span>
                    <span className="text-foreground">{child.title}</span>
                  </div>
                </div>
                <StatusBadge status={child.status} />
              </Link>
            ))}
          </div>
        </SectionCard>
      )}

      {requirement.linked_test_runs && requirement.linked_test_runs.length > 0 && (
        <SectionCard title="Linked Test Runs">
          <div className="overflow-x-auto -mx-6">
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
                      {formatDateTime(tr.created_at)} ago
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
        </SectionCard>
      )}

      <DocumentActivityPanel artefactType="requirement" artefactId={reqId} />

      <DocumentLinksPanel
        projectId={requirement.project_id}
        projectPrefix={projectPrefix}
        sourceType="REQ"
        sourceId={reqId}
        derivedLinks={derivedMembershipLinks}
      />
    </DocDetailShell>
    {toast && (
      <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-md shadow-lg text-sm border"
        style={{
          background: toast.variant === 'success' ? 'var(--color-emerald-50, #ecfdf5)' : toast.variant === 'error' ? 'var(--color-red-50, #fef2f2)' : 'var(--color-blue-50, #eff6ff)',
          borderColor: toast.variant === 'success' ? 'var(--color-emerald-200, #a7f3d0)' : toast.variant === 'error' ? 'var(--color-red-200, #fecaca)' : 'var(--color-blue-200, #bfdbfe)',
        }}
      >
        <div className={`w-2 h-2 rounded-full ${toast.variant === 'success' ? 'bg-emerald-500' : toast.variant === 'error' ? 'bg-red-500' : 'bg-blue-500'}`} />
        <span className={toast.variant === 'success' ? 'text-emerald-800' : toast.variant === 'error' ? 'text-red-800' : 'text-blue-800'}>
          {toast.message}
        </span>
        <button onClick={() => setToast(null)} className="ml-3 text-xs underline opacity-60 hover:opacity-100">Dismiss</button>
      </div>
    )}
    </>
  )
}
