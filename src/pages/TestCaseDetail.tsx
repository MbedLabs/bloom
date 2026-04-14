import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { testCasesApi } from '../api/client'
import { ArrowLeft, Pencil, FileText } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function TestCaseDetail() {
  const { id } = useParams<{ id: string }>()
  const tcId = parseInt(id || '0')
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
  })

  useEffect(() => {
    if (testCase && isEditing) {
      setEditForm({
        title: testCase.title,
        description: testCase.description || '',
        preconditions: testCase.preconditions || '',
        status: testCase.status,
      })
    }
  }, [testCase, isEditing])

  const updateMutation = useMutation({
    mutationFn: (data: Parameters<typeof testCasesApi.update>[1]) => testCasesApi.update(tcId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCase', tcId] })
      setIsEditing(false)
    },
  })

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate({
      title: editForm.title,
      description: editForm.description || null,
      preconditions: editForm.preconditions || null,
      status: editForm.status,
    })
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-gray-500">Loading...</div>
  }

  if (error || !testCase) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-red-900">Test Case Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-teal-600 hover:text-teal-700">
          ← Back to Projects
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${testCase.project_id}`} className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </Link>
          <div>
            <div className="flex items-center space-x-3">
              <span className="font-mono text-sm text-teal-600 font-semibold">{testCase.tc_id}</span>
              <TcStatusBadge status={testCase.status} />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mt-1">{testCase.title}</h2>
          </div>
        </div>
        <button
          onClick={() => setIsEditing(true)}
          className="inline-flex items-center px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors text-sm"
        >
          <Pencil className="h-4 w-4 mr-2" />
          Edit
        </button>
      </div>

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
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Preconditions</label>
              <textarea
                value={editForm.preconditions}
                onChange={(e) => setEditForm({ ...editForm, preconditions: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                rows={2}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={editForm.status}
                onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              >
                <option>Draft</option>
                <option>Active</option>
                <option>Deprecated</option>
              </select>
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
        <>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Description</h3>
            <p className="text-gray-900 whitespace-pre-wrap">
              {testCase.description || 'No description provided.'}
            </p>
          </div>

          {testCase.preconditions && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Preconditions</h3>
              <p className="text-gray-900 whitespace-pre-wrap">{testCase.preconditions}</p>
            </div>
          )}
        </>
      )}

      {testCase.steps && testCase.steps.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold">Steps</h3>
          </div>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-20">Step</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expected Result</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {testCase.steps.map((step) => (
                <tr key={step.step_number} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {step.step_number}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700 whitespace-pre-wrap">
                    {step.action}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700 whitespace-pre-wrap">
                    {step.expected_result}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-semibold">Linked Requirements</h3>
          <span className="text-sm text-gray-500">{testCase.linked_requirements?.length || 0} linked</span>
        </div>
        {testCase.linked_requirements && testCase.linked_requirements.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {testCase.linked_requirements.map((req) => (
              <Link
                key={req.id}
                to={`/requirements/${req.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center">
                  <FileText className="h-5 w-5 text-teal-500 mr-3" />
                  <div>
                    <span className="font-mono text-sm text-teal-600 mr-2">{req.req_id}</span>
                    <span className="text-gray-900">{req.title}</span>
                  </div>
                </div>
                <RequirementStatusBadge status={req.status} />
              </Link>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center text-gray-500">
            No requirements linked to this test case.
          </div>
        )}
      </div>

      <div className="text-sm text-gray-500 flex items-center space-x-6">
        <span>Created {formatDistanceToNow(new Date(testCase.created_at))} ago</span>
        <span>Updated {formatDistanceToNow(new Date(testCase.updated_at))} ago</span>
      </div>
    </div>
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
