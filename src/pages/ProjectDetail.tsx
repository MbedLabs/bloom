import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, requirementsApi, testCasesApi } from '../api/client'
import { ArrowLeft, Plus, FileText, CheckCircle, GitBranch, Search, BookOpen, Beaker } from 'lucide-react'

type Tab = 'requirements' | 'test-cases' | 'documents' | 'test-concepts' | 'traceability'

interface TestConcept {
  id: number
  name: string
  description: string
  linkedRequirementIds: number[]
  coverage: number
  status: string
}

const MOCK_TC_KEY = 'bloom-test-concepts'

function loadTestConcepts(projectId: number): TestConcept[] {
  try {
    const raw = localStorage.getItem(`${MOCK_TC_KEY}-${projectId}`)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveTestConcepts(projectId: number, concepts: TestConcept[]) {
  localStorage.setItem(`${MOCK_TC_KEY}-${projectId}`, JSON.stringify(concepts))
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const projectId = parseInt(id || '0')
  const [activeTab, setActiveTab] = useState<Tab>('requirements')
  const [reqStatusFilter, setReqStatusFilter] = useState('')
  const [tcStatusFilter, setTcStatusFilter] = useState('')
  const [showCreateReq, setShowCreateReq] = useState(false)
  const [showCreateTc, setShowCreateTc] = useState(false)
  const [showCreateConcept, setShowCreateConcept] = useState(false)
  const [reqForm, setReqForm] = useState({ title: '', description: '', priority: 'Medium', req_type: 'Functional' })
  const [tcForm, setTcForm] = useState({ title: '', description: '', preconditions: '' })
  const [conceptForm, setConceptForm] = useState({ name: '', description: '' })
  const [testConcepts, setTestConcepts] = useState<TestConcept[]>(() => loadTestConcepts(projectId))
  const queryClient = useQueryClient()

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
    enabled: !!projectId,
  })

  const { data: requirements, isLoading: reqsLoading } = useQuery({
    queryKey: ['requirements', projectId],
    queryFn: () => requirementsApi.list(projectId),
    enabled: !!projectId,
  })

  const { data: testCases, isLoading: tcsLoading } = useQuery({
    queryKey: ['testCases', projectId],
    queryFn: () => testCasesApi.list(projectId),
    enabled: !!projectId,
  })

  const createReqMutation = useMutation({
    mutationFn: requirementsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowCreateReq(false)
      setReqForm({ title: '', description: '', priority: 'Medium', req_type: 'Functional' })
    },
  })

  const createTcMutation = useMutation({
    mutationFn: testCasesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCases', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowCreateTc(false)
      setTcForm({ title: '', description: '', preconditions: '' })
    },
  })

  const handleCreateReq = (e: React.FormEvent) => {
    e.preventDefault()
    createReqMutation.mutate({
      project_id: projectId,
      title: reqForm.title,
      description: reqForm.description || undefined,
      priority: reqForm.priority,
      req_type: reqForm.req_type,
    })
  }

  const handleCreateTc = (e: React.FormEvent) => {
    e.preventDefault()
    createTcMutation.mutate({
      project_id: projectId,
      title: tcForm.title,
      description: tcForm.description || undefined,
      preconditions: tcForm.preconditions || undefined,
    })
  }

  const handleCreateConcept = (e: React.FormEvent) => {
    e.preventDefault()
    const newConcept: TestConcept = {
      id: Date.now(),
      name: conceptForm.name,
      description: conceptForm.description,
      linkedRequirementIds: [],
      coverage: 0,
      status: 'Draft',
    }
    const updated = [...testConcepts, newConcept]
    setTestConcepts(updated)
    saveTestConcepts(projectId, updated)
    setShowCreateConcept(false)
    setConceptForm({ name: '', description: '' })
  }

  const filteredRequirements = requirements?.filter(r =>
    !reqStatusFilter || r.status === reqStatusFilter
  )

  const filteredTestCases = testCases?.filter(tc =>
    !tcStatusFilter || tc.status === tcStatusFilter
  )

  if (projectLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!project) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Project Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Projects
        </Link>
      </div>
    )
  }

  const tabs: { key: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { key: 'requirements', label: 'Requirements', icon: FileText },
    { key: 'test-cases', label: 'Test Cases', icon: CheckCircle },
    { key: 'documents', label: 'Documents', icon: BookOpen },
    { key: 'test-concepts', label: 'Test Concepts', icon: Beaker },
    { key: 'traceability', label: 'Traceability', icon: GitBranch },
  ]

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/projects" className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold text-foreground">{project.name}</h2>
            <p className="text-muted-foreground">{project.prefix}{project.description ? ` — ${project.description}` : ''}</p>
          </div>
        </div>
        <ProjectStatusBadge status={project.status} />
      </div>

      <div className="border-b border-border">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center py-3 px-1 border-b-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <tab.icon className="h-4 w-4 mr-2" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'requirements' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <select
                  value={reqStatusFilter}
                  onChange={(e) => setReqStatusFilter(e.target.value)}
                  className="pl-9 pr-8 py-2 bg-background border border-input rounded-md text-sm focus:ring-2 focus:ring-ring focus:border-ring appearance-none"
                >
                  <option value="">All Statuses</option>
                  <option value="Draft">Draft</option>
                  <option value="Review">Review</option>
                  <option value="Approved">Approved</option>
                  <option value="Implemented">Implemented</option>
                  <option value="Verified">Verified</option>
                  <option value="Rejected">Rejected</option>
                </select>
              </div>
              <span className="text-sm text-muted-foreground">
                {filteredRequirements?.length || 0} requirement{(filteredRequirements?.length || 0) !== 1 ? 's' : ''}
              </span>
            </div>
            <button
              onClick={() => setShowCreateReq(true)}
              className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Requirement
            </button>
          </div>

          {reqsLoading ? (
            <div className="bg-card rounded-lg shadow-elegant p-6 text-center text-muted-foreground">Loading...</div>
          ) : !filteredRequirements || filteredRequirements.length === 0 ? (
            <div className="bg-card rounded-lg shadow-elegant p-12 text-center">
              <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium text-foreground mb-2">No Requirements</h3>
              <p className="text-muted-foreground">Create your first requirement for this project.</p>
            </div>
          ) : (
            <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">ID</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Title</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Priority</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">TCs</th>
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {filteredRequirements.map((req) => (
                    <tr key={req.id} className="hover:bg-accent/50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Link to={`/requirements/${req.id}`} className="text-primary hover:text-primary/80 font-mono text-sm font-medium">
                          {req.req_id}
                        </Link>
                      </td>
                      <td className="px-6 py-4">
                        <Link to={`/requirements/${req.id}`} className="text-foreground hover:text-primary/80 font-medium">
                          {req.title}
                        </Link>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <RequirementStatusBadge status={req.status} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <PriorityBadge priority={req.priority} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{req.req_type}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{req.test_case_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'test-cases' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <select
                value={tcStatusFilter}
                onChange={(e) => setTcStatusFilter(e.target.value)}
                className="px-3 py-2 bg-background border border-input rounded-md text-sm focus:ring-2 focus:ring-ring focus:border-ring"
              >
                <option value="">All Statuses</option>
                <option value="Draft">Draft</option>
                <option value="Active">Active</option>
                <option value="Deprecated">Deprecated</option>
              </select>
              <span className="text-sm text-muted-foreground">
                {filteredTestCases?.length || 0} test case{(filteredTestCases?.length || 0) !== 1 ? 's' : ''}
              </span>
            </div>
            <button
              onClick={() => setShowCreateTc(true)}
              className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Test Case
            </button>
          </div>

          {tcsLoading ? (
            <div className="bg-card rounded-lg shadow-elegant p-6 text-center text-muted-foreground">Loading...</div>
          ) : !filteredTestCases || filteredTestCases.length === 0 ? (
            <div className="bg-card rounded-lg shadow-elegant p-12 text-center">
              <CheckCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium text-foreground mb-2">No Test Cases</h3>
              <p className="text-muted-foreground">Create your first test case for this project.</p>
            </div>
          ) : (
            <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">ID</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Title</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Requirements</th>
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {filteredTestCases.map((tc) => (
                    <tr key={tc.id} className="hover:bg-accent/50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Link to={`/test-cases/${tc.id}`} className="text-primary hover:text-primary/80 font-mono text-sm font-medium">
                          {tc.tc_id}
                        </Link>
                      </td>
                      <td className="px-6 py-4">
                        <Link to={`/test-cases/${tc.id}`} className="text-foreground hover:text-primary/80 font-medium">
                          {tc.title}
                        </Link>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <TcStatusBadge status={tc.status} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{tc.requirement_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'documents' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">
              Manage project documents, specifications, and test concepts
            </span>
            <Link
              to={`/projects/${projectId}/documents`}
              className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 hover:shadow-glow transition-all duration-200 text-sm font-medium"
            >
              <BookOpen className="h-4 w-4 mr-2" />
              Open Documents
            </Link>
          </div>

          <div className="bg-card rounded-lg border border-border shadow-elegant p-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-4">
              <BookOpen className="h-8 w-8 text-primary/40" />
            </div>
            <h3 className="text-lg font-medium text-foreground mb-2">Document Management</h3>
            <p className="text-muted-foreground max-w-md mx-auto mb-5">
              Create and manage structured documents with traceable sections. Link sections to requirements for full lifecycle coverage.
            </p>
            <Link
              to={`/projects/${projectId}/documents`}
              className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors text-sm font-medium"
            >
              Go to Documents
            </Link>
          </div>
        </div>
      )}

      {activeTab === 'test-concepts' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">
              {testConcepts.length} test concept{testConcepts.length !== 1 ? 's' : ''}
            </span>
            <button
              onClick={() => setShowCreateConcept(true)}
              className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Test Concept
            </button>
          </div>

          {testConcepts.length === 0 ? (
            <div className="bg-card rounded-lg shadow-elegant p-12 text-center">
              <Beaker className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium text-foreground mb-2">No Test Concepts</h3>
              <p className="text-muted-foreground">Create your first test concept for this project.</p>
            </div>
          ) : (
            <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Linked Requirements</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Coverage</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {testConcepts.map((concept) => (
                    <tr key={concept.id} className="hover:bg-accent/50">
                      <td className="px-6 py-4">
                        <div>
                          <span className="text-foreground font-medium">{concept.name}</span>
                          {concept.description && (
                            <p className="text-sm text-muted-foreground mt-0.5">{concept.description}</p>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                        {concept.linkedRequirementIds.length} requirement{concept.linkedRequirementIds.length !== 1 ? 's' : ''}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <CoverageBar coverage={concept.coverage} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <DocStatusBadge status={concept.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'traceability' && (
        <div className="bg-card rounded-lg shadow-elegant p-12 text-center">
          <GitBranch className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">Traceability Matrix</h3>
          <p className="text-muted-foreground mb-4">View the full coverage matrix for this project.</p>
          <Link
            to={`/traceability/${projectId}`}
            className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors"
          >
            View Traceability Matrix
          </Link>
        </div>
      )}

      {showCreateReq && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-elegant max-w-md w-full mx-4">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold">New Requirement</h3>
            </div>
            <form onSubmit={handleCreateReq}>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Title</label>
                  <input
                    type="text"
                    required
                    value={reqForm.title}
                    onChange={(e) => setReqForm({ ...reqForm, title: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                    placeholder="Requirement title"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Description</label>
                  <textarea
                    value={reqForm.description}
                    onChange={(e) => setReqForm({ ...reqForm, description: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                    rows={3}
                    placeholder="Requirement description..."
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Priority</label>
                    <select
                      value={reqForm.priority}
                      onChange={(e) => setReqForm({ ...reqForm, priority: e.target.value })}
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
                      value={reqForm.req_type}
                      onChange={(e) => setReqForm({ ...reqForm, req_type: e.target.value })}
                      className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                    >
                      <option>Functional</option>
                      <option>Non-Functional</option>
                      <option>Performance</option>
                      <option>Security</option>
                      <option>Usability</option>
                    </select>
                  </div>
                </div>
              </div>
              <div className="px-6 py-4 border-t border-border flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowCreateReq(false)}
                  className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createReqMutation.isPending}
                  className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
                >
                  {createReqMutation.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showCreateTc && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-elegant max-w-md w-full mx-4">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold">New Test Case</h3>
            </div>
            <form onSubmit={handleCreateTc}>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Title</label>
                  <input
                    type="text"
                    required
                    value={tcForm.title}
                    onChange={(e) => setTcForm({ ...tcForm, title: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                    placeholder="Test case title"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Description</label>
                  <textarea
                    value={tcForm.description}
                    onChange={(e) => setTcForm({ ...tcForm, description: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                    rows={3}
                    placeholder="Test case description..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Preconditions</label>
                  <textarea
                    value={tcForm.preconditions}
                    onChange={(e) => setTcForm({ ...tcForm, preconditions: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                    rows={2}
                    placeholder="Preconditions for this test..."
                  />
                </div>
              </div>
              <div className="px-6 py-4 border-t border-border flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowCreateTc(false)}
                  className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createTcMutation.isPending}
                  className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
                >
                  {createTcMutation.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showCreateConcept && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-elegant max-w-md w-full mx-4">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold">New Test Concept</h3>
            </div>
            <form onSubmit={handleCreateConcept}>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Name</label>
                  <input
                    type="text"
                    required
                    value={conceptForm.name}
                    onChange={(e) => setConceptForm({ ...conceptForm, name: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                    placeholder="Test concept name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Description</label>
                  <textarea
                    value={conceptForm.description}
                    onChange={(e) => setConceptForm({ ...conceptForm, description: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-ring"
                    rows={3}
                    placeholder="Test concept description..."
                  />
                </div>
              </div>
              <div className="px-6 py-4 border-t border-border flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowCreateConcept(false)}
                  className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function ProjectStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Active: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Archived: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Draft: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
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

function DocStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Draft: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Review: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Approved: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>
      {status}
    </span>
  )
}

function CoverageBar({ coverage }: { coverage: number }) {
  const color = coverage >= 80 ? 'bg-teal-500' : coverage >= 50 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center space-x-2">
      <div className="w-24 bg-border rounded-full h-2">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${coverage}%` }} />
      </div>
      <span className="text-sm text-muted-foreground">{coverage}%</span>
    </div>
  )
}
