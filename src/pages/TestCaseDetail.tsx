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
        <button
          onClick={() => setIsEditing(true)}
          className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
        >
          <Pencil className="h-4 w-4 mr-2" />
          Edit
        </button>
      </div>

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
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Preconditions</label>
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

      {testCase.steps && testCase.steps.length > 0 && (
        <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
          <div className="px-6 py-4 border-b border-border">
            <h3 className="text-lg font-semibold">Steps</h3>
          </div>
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase w-20">Step</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Action</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Expected Result</th>
              </tr>
            </thead>
            <tbody className="bg-card divide-y divide-border">
              {testCase.steps.map((step) => (
                <tr key={step.step_number} className="hover:bg-accent/50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                    {step.step_number}
                  </td>
                  <td className="px-6 py-4 text-sm text-foreground whitespace-pre-wrap">
                    {step.action}
                  </td>
                  <td className="px-6 py-4 text-sm text-foreground whitespace-pre-wrap">
                    {step.expected_result}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-card rounded-lg shadow-elegant">
        <div className="px-6 py-4 border-b border-border flex justify-between items-center">
          <h3 className="text-lg font-semibold">Linked Requirements</h3>
          <span className="text-sm text-muted-foreground">{testCase.linked_requirements?.length || 0} linked</span>
        </div>
        {testCase.linked_requirements && testCase.linked_requirements.length > 0 ? (
          <div className="divide-y divide-border">
            {testCase.linked_requirements.map((req) => (
              <Link
                key={req.id}
                to={`/requirements/${req.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center">
                  <FileText className="h-5 w-5 text-primary mr-3" />
                  <div>
                    <span className="font-mono text-sm text-primary mr-2">{req.req_id}</span>
                    <span className="text-foreground">{req.title}</span>
                  </div>
                </div>
                <RequirementStatusBadge status={req.status} />
              </Link>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center text-muted-foreground">
            No requirements linked to this test case.
          </div>
        )}
      </div>

      <div className="text-sm text-muted-foreground flex items-center space-x-6">
        <span>Created {formatDistanceToNow(new Date(testCase.created_at))} ago</span>
        <span>Updated {formatDistanceToNow(new Date(testCase.updated_at))} ago</span>
      </div>
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
