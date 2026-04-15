import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { requirementsApi, testCasesApi } from '../api/client'
import { ArrowLeft, Pencil, Link2, ExternalLink, ChevronRight, CheckCircle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function RequirementDetail() {
  const { id } = useParams<{ id: string }>()
  const reqId = parseInt(id || '0')
  const queryClient = useQueryClient()

  const { data: requirement, isLoading, error } = useQuery({
    queryKey: ['requirement', reqId],
    queryFn: () => requirementsApi.get(reqId),
    enabled: !!reqId,
  })

  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    title: '',
    description: '',
    status: '',
    priority: '',
    req_type: '',
    req_origin: '',
  })
  const [showLinkModal, setShowLinkModal] = useState(false)

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
    mutationFn: (testCaseId: number) => requirementsApi.linkTestCase(reqId, testCaseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirement', reqId] })
      setShowLinkModal(false)
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
    })

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

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${requirement.project_id}`} className="p-2 hover:bg-accent/50 rounded-md">
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

      {requirement.parent_id && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <span className="text-sm text-blue-600 font-medium">Parent Requirement: </span>
          <Link to={`/requirements/${requirement.parent_id}`} className="text-sm text-primary hover:text-primary/80 font-medium">
            View Parent →
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
            <div className="grid grid-cols-4 gap-4">
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
                to={`/requirements/${child.id}`}
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
          <h3 className="text-lg font-semibold">Linked Test Cases</h3>
          <span className="text-sm text-muted-foreground">{requirement.linked_test_cases?.length || 0} linked</span>
        </div>
        {requirement.linked_test_cases && requirement.linked_test_cases.length > 0 ? (
          <div className="divide-y divide-border">
            {requirement.linked_test_cases.map((tc) => (
              <Link
                key={tc.id}
                to={`/test-cases/${tc.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-primary mr-3" />
                  <div>
                    <span className="font-mono text-sm text-primary mr-2">{tc.tc_id}</span>
                    <span className="text-foreground">{tc.title}</span>
                  </div>
                </div>
                <TcStatusBadge status={tc.status} />
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
              {unlinkedTestCases.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  <CheckCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p>All test cases are already linked.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {unlinkedTestCases.map((tc) => (
                    <button
                      key={tc.id}
                      onClick={() => linkTcMutation.mutate(tc.id)}
                      disabled={linkTcMutation.isPending}
                      className="w-full flex items-center justify-between px-4 py-3 rounded-md border border-border hover:border-primary/50 hover:bg-primary/10 transition-colors text-left disabled:opacity-50"
                    >
                      <div>
                        <span className="font-mono text-sm text-primary mr-2">{tc.tc_id}</span>
                        <span className="text-foreground">{tc.title}</span>
                      </div>
                      <Link2 className="h-4 w-4 text-muted-foreground" />
                    </button>
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
