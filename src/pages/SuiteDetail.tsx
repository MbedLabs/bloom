import { useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, FlaskConical, Layers3, Pencil, Plus, Trash2 } from 'lucide-react'

import { campaignsApi, testCasesApi, testSuitesApi } from '../api/client'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'
import { docUrl } from '../types/doc'

const SUITE_STATUSES = ['Draft', 'Active', 'Archived']

export default function SuiteDetail() {
  const { prefix, suiteId } = useParams<{ prefix: string; suiteId: string }>()
  const { data: project } = useProjectByPrefix(prefix)
  const projectId = project?.id || 0
  const parsedSuiteId = Number(suiteId)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [showAddCase, setShowAddCase] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({ name: '', description: '', status: '' })
  const [confirmDelete, setConfirmDelete] = useState(false)

  const { data: suite, isLoading } = useQuery({
    queryKey: ['testSuite', parsedSuiteId],
    queryFn: () => testSuitesApi.get(parsedSuiteId),
    enabled: !!parsedSuiteId,
  })

  const { data: testCases } = useQuery({
    queryKey: ['testCases', projectId],
    queryFn: () => testCasesApi.list(projectId),
    enabled: !!projectId,
  })

  const addItemMutation = useMutation({
    mutationFn: (testCaseId: number) => testSuitesApi.addItem(parsedSuiteId, testCaseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testSuite', parsedSuiteId] })
      queryClient.invalidateQueries({ queryKey: ['testSuites', projectId] })
      queryClient.invalidateQueries({ queryKey: ['testCases', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowAddCase(false)
    },
  })

  const removeItemMutation = useMutation({
    mutationFn: (itemId: number) => testSuitesApi.removeItem(parsedSuiteId, itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testSuite', parsedSuiteId] })
      queryClient.invalidateQueries({ queryKey: ['testSuites', projectId] })
      queryClient.invalidateQueries({ queryKey: ['testCases', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    },
  })

  const launchCampaignMutation = useMutation({
    mutationFn: () => campaignsApi.create({
      project_id: projectId,
      name: `${suite?.name || 'Suite'} Scope ${new Date().toISOString().slice(0, 10)}`,
      description: `Traceability scope campaign from suite ${suite?.suite_id || ''}`,
      suite_ids: [parsedSuiteId],
      status: 'Scope',
    }),
    onSuccess: (campaign) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns', projectId] })
      queryClient.invalidateQueries({ queryKey: ['testSuite', parsedSuiteId] })
      window.location.href = `/projects/${prefix}/campaigns/${campaign.id}`
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: { name?: string; description?: string; status?: string }) =>
      testSuitesApi.update(parsedSuiteId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testSuite', parsedSuiteId] })
      queryClient.invalidateQueries({ queryKey: ['testSuites', projectId] })
      setEditing(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => testSuitesApi.delete(parsedSuiteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testSuites', projectId] })
      navigate(`/projects/${prefix}/campaigns`)
    },
  })

  const startEdit = () => {
    if (!suite) return
    setEditForm({ name: suite.name, description: suite.description || '', status: suite.status })
    setEditing(true)
  }

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate({
      name: editForm.name,
      description: editForm.description || undefined,
      status: editForm.status,
    })
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!suite) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Suite Not Found</h3>
        <Link to={`/projects/${prefix}/campaigns`} className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Campaigns
        </Link>
      </div>
    )
  }

  const includedCaseIds = new Set(suite.items.map((item) => item.test_case_id))
  const availableCases = (testCases || []).filter((tc) => !includedCaseIds.has(tc.id))

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to={`/projects/${prefix}/campaigns`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <div className="font-mono text-sm text-primary">{suite.suite_id}</div>
            <h2 className="text-2xl font-bold text-foreground mt-1">{suite.name}</h2>
            {suite.description && <p className="text-muted-foreground mt-1">{suite.description}</p>}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={startEdit} className="inline-flex items-center px-3 py-1.5 border border-input text-foreground rounded-md hover:bg-accent/50 text-sm">
            <Pencil className="h-3.5 w-3.5 mr-1.5" /> Edit
          </button>
          <button onClick={() => setConfirmDelete(true)} className="inline-flex items-center px-3 py-1.5 border border-destructive/30 text-destructive rounded-md hover:bg-destructive/10 text-sm">
            <Trash2 className="h-3.5 w-3.5 mr-1.5" /> Delete
          </button>
          <button
            onClick={() => setShowAddCase(true)}
            className="inline-flex items-center px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50 text-sm"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Test Case
          </button>
          <button
            onClick={() => launchCampaignMutation.mutate()}
            disabled={launchCampaignMutation.isPending}
            className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm disabled:opacity-50"
          >
            <Layers3 className="h-4 w-4 mr-2" />
            Create Campaign Scope
          </button>
        </div>
      </div>

      {editing && (
        <div className="bg-card rounded-lg shadow-elegant p-5">
          <h3 className="text-sm font-medium text-muted-foreground mb-3">Edit Suite</h3>
          <form onSubmit={handleEditSubmit} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Name</label>
              <input type="text" required value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Description</label>
              <textarea value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring" rows={2} />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Status</label>
              <select value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring">
                {SUITE_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setEditing(false)} className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50 text-sm">Cancel</button>
              <button type="submit" disabled={updateMutation.isPending} className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 text-sm">{updateMutation.isPending ? 'Saving...' : 'Save'}</button>
            </div>
          </form>
        </div>
      )}

      {confirmDelete && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-elegant p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold text-foreground mb-2">Delete Suite?</h3>
            <p className="text-sm text-muted-foreground mb-4">This action cannot be undone. All suite items will be removed.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDelete(false)} className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50 text-sm">Cancel</button>
              <button onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending} className="px-4 py-2 bg-destructive text-white rounded-md hover:bg-destructive/90 disabled:opacity-50 text-sm">{deleteMutation.isPending ? 'Deleting...' : 'Delete'}</button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <SummaryCard label="Suite Items" value={suite.total_items} />
        <SummaryCard label="Related Requirements" value={suite.related_requirements.length} />
        <SummaryCard label="Linked Campaigns" value={suite.linked_campaigns.length} />
      </div>

      <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
        <div className="px-6 py-4 border-b border-border">
          <h3 className="text-lg font-semibold">Suite Test Cases</h3>
        </div>
        {suite.items.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">No test cases in this suite.</div>
        ) : (
          <div className="divide-y divide-border">
            {suite.items.map((item) => (
              <div key={item.id} className="px-6 py-4 flex items-center justify-between gap-4">
                <div>
                  <div className="text-xs text-muted-foreground">#{item.order + 1}</div>
                  {item.test_case && (
                    <>
                      <Link to={docUrl(prefix!, 'TC', item.test_case.tc_id)} className="font-mono text-sm text-primary hover:text-primary/80">
                        {item.test_case.tc_id}
                      </Link>
                      <div className="text-foreground mt-1">{item.test_case.title}</div>
                    </>
                  )}
                </div>
                <button
                  onClick={() => removeItemMutation.mutate(item.id)}
                  disabled={removeItemMutation.isPending}
                  className="inline-flex items-center px-3 py-2 rounded-md border border-red-300 text-red-600 hover:bg-red-50 text-sm disabled:opacity-50"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
          <div className="px-6 py-4 border-b border-border">
            <h3 className="text-lg font-semibold">Related Requirements</h3>
          </div>
          {suite.related_requirements.length === 0 ? (
            <div className="p-6 text-center text-muted-foreground">No requirements mapped via suite test cases.</div>
          ) : (
            <div className="divide-y divide-border">
              {suite.related_requirements.map((req) => (
                <Link key={req.id} to={docUrl(prefix!, 'REQ', req.req_id)} className="block px-6 py-4 hover:bg-accent/40">
                  <div className="font-mono text-sm text-primary">{req.req_id}</div>
                  <div className="text-foreground mt-1">{req.title}</div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
          <div className="px-6 py-4 border-b border-border">
            <h3 className="text-lg font-semibold">Linked Campaigns</h3>
          </div>
          {suite.linked_campaigns.length === 0 ? (
            <div className="p-6 text-center text-muted-foreground">No campaigns created from this suite yet.</div>
          ) : (
            <div className="divide-y divide-border">
              {suite.linked_campaigns.map((campaign) => (
                <Link key={campaign.id} to={`/projects/${prefix}/campaigns/${campaign.id}`} className="block px-6 py-4 hover:bg-accent/40">
                  <div className="font-medium text-foreground">{campaign.name}</div>
                  <div className="text-xs text-muted-foreground mt-1">{campaign.status}</div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {suite.related_concepts && suite.related_concepts.length > 0 && (
        <div className="bg-card rounded-lg shadow-elegant p-5">
          <h3 className="text-sm font-medium text-muted-foreground mb-3">Related Concepts</h3>
          <div className="flex flex-wrap gap-2">
            {suite.related_concepts.map((concept) => (
              <Link key={concept.id} to={docUrl(prefix!, 'TCO', concept.concept_id)} className="inline-flex items-center px-3 py-2 rounded-md bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 hover:bg-cyan-500/15 text-sm">
                <FlaskConical className="h-3.5 w-3.5 mr-1.5" />
                <span className="font-mono mr-2">{concept.concept_id}</span>
                {concept.name}
              </Link>
            ))}
          </div>
        </div>
      )}

      {showAddCase && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-card rounded-lg shadow-elegant max-w-lg w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold">Add Test Case To Suite</h3>
            </div>
            <div className="p-6 overflow-y-auto flex-1">
              {availableCases.length === 0 ? (
                <div className="text-center text-muted-foreground py-6">No available test cases.</div>
              ) : (
                <div className="space-y-2">
                  {availableCases.map((tc) => (
                    <button
                      key={tc.id}
                      onClick={() => addItemMutation.mutate(tc.id)}
                      className="w-full text-left px-4 py-3 rounded-md border border-border hover:border-primary/50 hover:bg-primary/10"
                    >
                      <div className="font-mono text-xs text-primary">{tc.tc_id}</div>
                      <div className="text-foreground mt-1">{tc.title}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="px-6 py-4 border-t border-border flex justify-end">
              <button onClick={() => setShowAddCase(false)} className="px-4 py-2 border border-input rounded-md hover:bg-accent/50">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-card rounded-lg border border-border shadow-elegant p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-2xl font-bold text-foreground mt-2">{value}</div>
    </div>
  )
}
