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
    })
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-gray-500">Loading...</div>
  }

  if (error || !requirement) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-red-900">Requirement Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-teal-600 hover:text-teal-700">
          ← Back to Projects
        </Link>
      </div>
    )
  }

  const linkedTcIds = new Set(requirement.linked_test_cases?.map(tc => tc.id) || [])
  const unlinkedTestCases = availableTestCases?.filter(tc => !linkedTcIds.has(tc.id)) || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${requirement.project_id}`} className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </Link>
          <div>
            <div className="flex items-center space-x-3">
              <span className="font-mono text-sm text-teal-600 font-semibold">{requirement.req_id}</span>
              <RequirementStatusBadge status={requirement.status} />
              <PriorityBadge priority={requirement.priority} />
              <TypeBadge reqType={requirement.req_type} />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mt-1">{requirement.title}</h2>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowLinkModal(true)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors text-sm"
          >
            <Link2 className="h-4 w-4 mr-2" />
            Link Test Case
          </button>
          <button
            onClick={() => setIsEditing(true)}
            className="inline-flex items-center px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors text-sm"
          >
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </button>
        </div>
      </div>

      {requirement.parent_id && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <span className="text-sm text-blue-600 font-medium">Parent Requirement: </span>
          <Link to={`/requirements/${requirement.parent_id}`} className="text-sm text-teal-600 hover:text-teal-700 font-medium">
            View Parent →
          </Link>
        </div>
      )}

      {isEditing ? (
        <div className="bg-white rounded-lg shadow p-6">
          <form onSubmit={handleEditSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
              <input
                type="text"
                required
                value={editForm.title}
                onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={editForm.description}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                rows={4}
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select
                  value={editForm.status}
                  onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
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
                <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                <select
                  value={editForm.priority}
                  onChange={(e) => setEditForm({ ...editForm, priority: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                >
                  <option>Low</option>
                  <option>Medium</option>
                  <option>High</option>
                  <option>Critical</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                <select
                  value={editForm.req_type}
                  onChange={(e) => setEditForm({ ...editForm, req_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                >
                  <option>Functional</option>
                  <option>Non-Functional</option>
                  <option>Performance</option>
                  <option>Security</option>
                  <option>Usability</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={updateMutation.isPending}
                className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50"
              >
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Description</h3>
          <p className="text-gray-900 whitespace-pre-wrap">
            {requirement.description || 'No description provided.'}
          </p>
          <div className="mt-4 pt-4 border-t border-gray-100 flex items-center space-x-6 text-sm text-gray-500">
            <span>Created {formatDistanceToNow(new Date(requirement.created_at))} ago</span>
            <span>Updated {formatDistanceToNow(new Date(requirement.updated_at))} ago</span>
          </div>
        </div>
      )}

      {requirement.children && requirement.children.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold">Child Requirements</h3>
          </div>
          <div className="divide-y divide-gray-200">
            {requirement.children.map((child) => (
              <Link
                key={child.id}
                to={`/requirements/${child.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center">
                  <ChevronRight className="h-4 w-4 text-gray-400 mr-3" />
                  <div>
                    <span className="font-mono text-sm text-teal-600 mr-2">{child.req_id}</span>
                    <span className="text-gray-900">{child.title}</span>
                  </div>
                </div>
                <RequirementStatusBadge status={child.status} />
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-semibold">Linked Test Cases</h3>
          <span className="text-sm text-gray-500">{requirement.linked_test_cases?.length || 0} linked</span>
        </div>
        {requirement.linked_test_cases && requirement.linked_test_cases.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {requirement.linked_test_cases.map((tc) => (
              <Link
                key={tc.id}
                to={`/test-cases/${tc.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-teal-500 mr-3" />
                  <div>
                    <span className="font-mono text-sm text-teal-600 mr-2">{tc.tc_id}</span>
                    <span className="text-gray-900">{tc.title}</span>
                  </div>
                </div>
                <TcStatusBadge status={tc.status} />
              </Link>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center text-gray-500">
            No test cases linked yet.
          </div>
        )}
      </div>

      {requirement.linked_test_runs && requirement.linked_test_runs.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold">Linked Test Runs</h3>
          </div>
          <div className="overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Test Run</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Link</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {requirement.linked_test_runs.map((tr) => (
                  <tr key={tr.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {tr.test_run_name || `Test Run #${tr.test_run_id}`}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {tr.status ? <RunStatusBadge status={tr.status} /> : '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatDistanceToNow(new Date(tr.created_at))} ago
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {tr.teststation_url ? (
                        <a
                          href={tr.teststation_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center text-teal-600 hover:text-teal-700"
                        >
                          <ExternalLink className="h-4 w-4 mr-1" />
                          Open
                        </a>
                      ) : (
                        <span className="text-gray-400">-</span>
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
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[80vh] flex flex-col">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-semibold">Link Test Case</h3>
              <button onClick={() => setShowLinkModal(false)} className="text-gray-400 hover:text-gray-600">
                ✕
              </button>
            </div>
            <div className="overflow-y-auto p-6">
              {unlinkedTestCases.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <CheckCircle className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                  <p>All test cases are already linked.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {unlinkedTestCases.map((tc) => (
                    <button
                      key={tc.id}
                      onClick={() => linkTcMutation.mutate(tc.id)}
                      disabled={linkTcMutation.isPending}
                      className="w-full flex items-center justify-between px-4 py-3 rounded-lg border border-gray-200 hover:border-teal-400 hover:bg-teal-50 transition-colors text-left disabled:opacity-50"
                    >
                      <div>
                        <span className="font-mono text-sm text-teal-600 mr-2">{tc.tc_id}</span>
                        <span className="text-gray-900">{tc.title}</span>
                      </div>
                      <Link2 className="h-4 w-4 text-gray-400" />
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
    Draft: 'bg-gray-100 text-gray-800',
    Review: 'bg-amber-100 text-amber-800',
    Approved: 'bg-blue-100 text-blue-800',
    Implemented: 'bg-teal-100 text-teal-800',
    Verified: 'bg-emerald-100 text-emerald-800',
    Rejected: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
      {status}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    Low: 'bg-gray-100 text-gray-800',
    Medium: 'bg-blue-100 text-blue-800',
    High: 'bg-orange-100 text-orange-800',
    Critical: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[priority] || 'bg-gray-100 text-gray-800'}`}>
      {priority}
    </span>
  )
}

function TypeBadge({ reqType }: { reqType: string }) {
  return (
    <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
      {reqType}
    </span>
  )
}

function TcStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Draft: 'bg-gray-100 text-gray-800',
    Active: 'bg-emerald-100 text-emerald-800',
    Deprecated: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
      {status}
    </span>
  )
}

function RunStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Passed: 'bg-emerald-100 text-emerald-800',
    Failed: 'bg-red-100 text-red-800',
    Running: 'bg-blue-100 text-blue-800',
    Pending: 'bg-gray-100 text-gray-800',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
      {status}
    </span>
  )
}
