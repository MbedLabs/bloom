import { ReactNode, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen,
  ArrowLeft,
  Beaker,
  CheckCircle,
  FileText,
  GitBranch,
  GitPullRequest,
  PenTool,
  Plus,
  Search,
  AlertTriangle,
} from 'lucide-react'

import {
  TestConcept as TestConceptRecord,
  changesApi,
  designsApi,
  documentsApi,
  requirementsApi,
  risksApi,
  projectsApi,
  testCasesApi,
  testConceptsApi,
  traceabilityApi,
  TcsRow,
} from '../api/client'
import { TcsArteTable } from '../components/TcsArteTable'
import { createDefaultTcRows } from '../utils/tcs'

type Tab = 'requirements' | 'test-cases' | 'documents' | 'test-concepts' | 'traceability' | 'design' | 'risks' | 'changes'

const VALID_TABS: Tab[] = ['requirements', 'test-cases', 'documents', 'test-concepts', 'traceability', 'design', 'risks', 'changes']

function getActiveTab(value: string | null): Tab {
  return VALID_TABS.includes(value as Tab) ? (value as Tab) : 'requirements'
}

export default function ProjectDetail() {
  const { prefix } = useParams<{ prefix: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = getActiveTab(searchParams.get('tab'))
  const queryClient = useQueryClient()

  const [reqStatusFilter, setReqStatusFilter] = useState('')
  const [tcStatusFilter, setTcStatusFilter] = useState('')
  const [showCreateReq, setShowCreateReq] = useState(false)
  const [showCreateTc, setShowCreateTc] = useState(false)
  const [showCreateConcept, setShowCreateConcept] = useState(false)
  const [showCreateDesign, setShowCreateDesign] = useState(false)
  const [showCreateRisk, setShowCreateRisk] = useState(false)
  const [showCreateChange, setShowCreateChange] = useState(false)

  const [reqForm, setReqForm] = useState({ title: '', description: '', priority: 'Medium', req_type: 'Functional', req_origin: 'Internal' })
  const [tcForm, setTcForm] = useState({ title: '', description: '', preconditions: '' })
  const [tcRows, setTcRows] = useState<TcsRow[]>(() => createDefaultTcRows())
  const [conceptForm, setConceptForm] = useState({ name: '', description: '', status: 'Draft', coverage: '0' })
  const [designForm, setDesignForm] = useState({ title: '', description: '', status: 'Draft', priority: 'Medium', design_type: 'Architecture', linked_requirement_id: '' })
  const [riskForm, setRiskForm] = useState({ title: '', description: '', status: 'Open', severity: 'Medium', probability: 'Medium', mitigation: '', risk_category: 'Technical', linked_requirement_id: '' })
  const [changeForm, setChangeForm] = useState({ title: '', description: '', status: 'Submitted', priority: 'Medium', change_type: 'Enhancement', impact_assessment: '', justification: '' })

  const setTab = (tab: Tab) => {
    const next = new URLSearchParams(searchParams)
    next.set('tab', tab)
    setSearchParams(next)
  }

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project-by-prefix', prefix],
    queryFn: () => projectsApi.getByPrefix(prefix!),
    enabled: !!prefix,
  })

  const projectId = project?.id || 0

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

  const { data: documents } = useQuery({
    queryKey: ['documents', projectId],
    queryFn: () => documentsApi.list(projectId),
    enabled: !!projectId,
  })

  const { data: matrix } = useQuery({
    queryKey: ['traceability', projectId],
    queryFn: () => traceabilityApi.getMatrix(projectId),
    enabled: !!projectId,
  })

  const { data: gapReport } = useQuery({
    queryKey: ['coverage-gaps', projectId],
    queryFn: () => traceabilityApi.getCoverageGaps(projectId),
    enabled: !!projectId,
  })

  const { data: designItems } = useQuery({
    queryKey: ['designs', projectId],
    queryFn: () => designsApi.list(projectId),
    enabled: !!projectId,
  })

  const { data: riskItems } = useQuery({
    queryKey: ['risks', projectId],
    queryFn: () => risksApi.list(projectId),
    enabled: !!projectId,
  })

  const { data: changeRequests } = useQuery({
    queryKey: ['changes', projectId],
    queryFn: () => changesApi.list(projectId),
    enabled: !!projectId,
  })

  const { data: testConcepts } = useQuery({
    queryKey: ['testConcepts', projectId],
    queryFn: () => testConceptsApi.list(projectId),
    enabled: !!projectId,
  })

  const createReqMutation = useMutation({
    mutationFn: requirementsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowCreateReq(false)
      setReqForm({ title: '', description: '', priority: 'Medium', req_type: 'Functional', req_origin: 'Internal' })
    },
  })

  const createTcMutation = useMutation({
    mutationFn: testCasesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCases', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowCreateTc(false)
      setTcForm({ title: '', description: '', preconditions: '' })
      setTcRows(createDefaultTcRows())
    },
  })

  const createDesignMutation = useMutation({
    mutationFn: designsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['designs', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowCreateDesign(false)
      setDesignForm({ title: '', description: '', status: 'Draft', priority: 'Medium', design_type: 'Architecture', linked_requirement_id: '' })
    },
  })

  const createRiskMutation = useMutation({
    mutationFn: risksApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risks', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowCreateRisk(false)
      setRiskForm({ title: '', description: '', status: 'Open', severity: 'Medium', probability: 'Medium', mitigation: '', risk_category: 'Technical', linked_requirement_id: '' })
    },
  })

  const createChangeMutation = useMutation({
    mutationFn: changesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['changes', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowCreateChange(false)
      setChangeForm({ title: '', description: '', status: 'Submitted', priority: 'Medium', change_type: 'Enhancement', impact_assessment: '', justification: '' })
    },
  })

  const createConceptMutation = useMutation({
    mutationFn: testConceptsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testConcepts', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowCreateConcept(false)
      setConceptForm({ name: '', description: '', status: 'Draft', coverage: '0' })
    },
  })

  const filteredRequirements = useMemo(
    () => requirements?.filter((item) => !reqStatusFilter || item.status === reqStatusFilter) ?? [],
    [requirements, reqStatusFilter]
  )

  const filteredTestCases = useMemo(
    () => testCases?.filter((item) => !tcStatusFilter || item.status === tcStatusFilter) ?? [],
    [testCases, tcStatusFilter]
  )

  const uncoveredRequirements = useMemo(
    () => matrix?.filter((item) => item.coverage_status !== 'Covered').slice(0, 6) ?? [],
    [matrix]
  )

  const handleCreateReq = (e: React.FormEvent) => {
    e.preventDefault()
    createReqMutation.mutate({
      project_id: projectId,
      title: reqForm.title,
      description: reqForm.description || undefined,
      priority: reqForm.priority,
      req_type: reqForm.req_type,
      req_origin: reqForm.req_origin,
    })
  }

  const handleCreateTc = (e: React.FormEvent) => {
    e.preventDefault()
    createTcMutation.mutate({
      project_id: projectId,
      title: tcForm.title,
      description: tcForm.description || undefined,
      preconditions: tcForm.preconditions || undefined,
      steps: tcRows.length > 0 ? tcRows : undefined,
    })
  }

  const handleCreateConcept = (e: React.FormEvent) => {
    e.preventDefault()
    createConceptMutation.mutate({
      project_id: projectId,
      name: conceptForm.name,
      description: conceptForm.description || null,
      status: conceptForm.status,
      linked_requirement_ids: [],
      coverage: Number(conceptForm.coverage) || 0,
    })
  }

  const handleCreateDesign = (e: React.FormEvent) => {
    e.preventDefault()
    createDesignMutation.mutate({
      project_id: projectId,
      title: designForm.title,
      description: designForm.description || null,
      status: designForm.status,
      priority: designForm.priority,
      design_type: designForm.design_type,
      linked_requirement_id: designForm.linked_requirement_id ? Number(designForm.linked_requirement_id) : null,
    })
  }

  const handleCreateRisk = (e: React.FormEvent) => {
    e.preventDefault()
    createRiskMutation.mutate({
      project_id: projectId,
      title: riskForm.title,
      description: riskForm.description || null,
      status: riskForm.status,
      severity: riskForm.severity,
      probability: riskForm.probability,
      mitigation: riskForm.mitigation || null,
      risk_category: riskForm.risk_category,
      linked_requirement_id: riskForm.linked_requirement_id ? Number(riskForm.linked_requirement_id) : null,
    })
  }

  const handleCreateChange = (e: React.FormEvent) => {
    e.preventDefault()
    createChangeMutation.mutate({
      project_id: projectId,
      title: changeForm.title,
      description: changeForm.description || null,
      status: changeForm.status,
      priority: changeForm.priority,
      change_type: changeForm.change_type,
      impact_assessment: changeForm.impact_assessment || null,
      justification: changeForm.justification || null,
    })
  }

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
    { key: 'design', label: 'Design', icon: PenTool },
    { key: 'risks', label: 'Risks', icon: AlertTriangle },
    { key: 'changes', label: 'Changes', icon: GitPullRequest },
    { key: 'documents', label: 'Documents', icon: BookOpen },
    { key: 'test-concepts', label: 'Test Concepts', icon: Beaker },
    { key: 'traceability', label: 'Traceability', icon: GitBranch },
  ]

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <Link to="/projects" className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold text-foreground">{project.name}</h2>
            <p className="text-muted-foreground">{project.prefix}{project.description ? ` - ${project.description}` : ''}</p>
          </div>
        </div>
        <ProjectStatusBadge status={project.status} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        <SummaryTile label="Requirements" value={project.requirement_count} />
        <SummaryTile label="Test Cases" value={project.test_case_count} />
        <SummaryTile label="Design" value={project.design_count} />
        <SummaryTile label="Risks" value={project.risk_count} />
        <SummaryTile label="Changes" value={project.change_count} />
        <SummaryTile label="Concepts" value={project.test_concept_count} />
      </div>

      <div className="border-b border-border overflow-x-auto">
        <nav className="flex space-x-8 min-w-max">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setTab(tab.key)}
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
          <SectionToolbar
            countLabel={`${filteredRequirements.length} requirement${filteredRequirements.length !== 1 ? 's' : ''}`}
            actionLabel="New Requirement"
            onAction={() => navigate(`/projects/${prefix}/docs/new?type=REQ`)}
          >
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <select
                value={reqStatusFilter}
                onChange={(e) => setReqStatusFilter(e.target.value)}
                className="pl-9 pr-8 py-2 bg-background border border-input rounded-md text-sm appearance-none"
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
          </SectionToolbar>

          {reqsLoading ? <LoadingCard /> : (
            <TableCard emptyTitle="No Requirements" emptyText="Create your first requirement for this project.">
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/50">
                  <tr>
                    <Th>ID</Th>
                    <Th>Title</Th>
                    <Th>Status</Th>
                    <Th>Priority</Th>
                    <Th>Type</Th>
                    <Th>Origin</Th>
                    <Th>TCs</Th>
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {filteredRequirements.map((req) => (
                    <tr key={req.id} className="hover:bg-accent/50">
                      <Td><Link to={`/projects/${prefix}/docs/${req.req_id}`} className="text-primary font-mono text-sm font-medium">{req.req_id}</Link></Td>
                      <Td><Link to={`/projects/${prefix}/docs/${req.req_id}`} className="text-foreground hover:text-primary/80 font-medium">{req.title}</Link></Td>
                      <Td><RequirementStatusBadge status={req.status} /></Td>
                      <Td><PriorityBadge priority={req.priority} /></Td>
                      <Td>{req.req_type}</Td>
                      <Td><OriginBadge origin={req.req_origin} /></Td>
                      <Td>{req.test_case_count}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableCard>
          )}
        </div>
      )}

      {activeTab === 'test-cases' && (
        <div className="space-y-4">
          <SectionToolbar
            countLabel={`${filteredTestCases.length} test case${filteredTestCases.length !== 1 ? 's' : ''}`}
            actionLabel="New Test Case"
            onAction={() => navigate(`/projects/${prefix}/docs/new?type=TC`)}
          >
            <select
              value={tcStatusFilter}
              onChange={(e) => setTcStatusFilter(e.target.value)}
              className="px-3 py-2 bg-background border border-input rounded-md text-sm"
            >
              <option value="">All Statuses</option>
              <option value="Draft">Draft</option>
              <option value="Active">Active</option>
              <option value="Deprecated">Deprecated</option>
            </select>
          </SectionToolbar>

          {tcsLoading ? <LoadingCard /> : (
            <TableCard emptyTitle="No Test Cases" emptyText="Create your first test case for this project.">
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/50">
                  <tr>
                    <Th>ID</Th>
                    <Th>Title</Th>
                    <Th>Status</Th>
                    <Th>Requirements</Th>
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {filteredTestCases.map((tc) => (
                    <tr key={tc.id} className="hover:bg-accent/50">
                      <Td><Link to={`/projects/${prefix}/docs/${tc.tc_id}`} className="text-primary font-mono text-sm font-medium">{tc.tc_id}</Link></Td>
                      <Td><Link to={`/projects/${prefix}/docs/${tc.tc_id}`} className="text-foreground hover:text-primary/80 font-medium">{tc.title}</Link></Td>
                      <Td><TcStatusBadge status={tc.status} /></Td>
                      <Td>{tc.requirement_count}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableCard>
          )}
        </div>
      )}

      {activeTab === 'design' && (
        <div className="space-y-4">
          <SectionToolbar countLabel={`${designItems?.length ?? 0} design item${(designItems?.length ?? 0) !== 1 ? 's' : ''}`} actionLabel="New Design Item" onAction={() => navigate(`/projects/${prefix}/docs/new?type=DES`)} />
          <TableCard emptyTitle="No Design Items" emptyText="Capture architecture, interfaces, and implementation design here.">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <Th>ID</Th>
                  <Th>Title</Th>
                  <Th>Type</Th>
                  <Th>Status</Th>
                  <Th>Priority</Th>
                  <Th>REQ</Th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {(designItems ?? []).map((item) => (
                  <tr key={item.id} className="hover:bg-accent/50">
                    <Td><Link to={`/projects/${prefix}/docs/${item.design_id}`} className="text-primary font-mono text-sm font-medium">{item.design_id}</Link></Td>
                    <Td><Link to={`/projects/${prefix}/docs/${item.design_id}`} className="text-foreground hover:text-primary/80 font-medium">{item.title}</Link></Td>
                    <Td>{item.design_type}</Td>
                    <Td><NeutralBadge value={item.status} /></Td>
                    <Td><PriorityBadge priority={item.priority} /></Td>
                    <Td>{item.linked_requirement_id ? `#${item.linked_requirement_id}` : '-'}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableCard>
        </div>
      )}

      {activeTab === 'risks' && (
        <div className="space-y-4">
          <SectionToolbar countLabel={`${riskItems?.length ?? 0} risk${(riskItems?.length ?? 0) !== 1 ? 's' : ''}`} actionLabel="New Risk" onAction={() => navigate(`/projects/${prefix}/docs/new?type=RSK`)} />
          <TableCard emptyTitle="No Risks" emptyText="Track technical, business, and compliance risks here.">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <Th>ID</Th>
                  <Th>Title</Th>
                  <Th>Status</Th>
                  <Th>Severity</Th>
                  <Th>Probability</Th>
                  <Th>Category</Th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {(riskItems ?? []).map((item) => (
                  <tr key={item.id} className="hover:bg-accent/50">
                    <Td><Link to={`/projects/${prefix}/docs/${item.risk_id}`} className="text-primary font-mono text-sm font-medium">{item.risk_id}</Link></Td>
                    <Td><Link to={`/projects/${prefix}/docs/${item.risk_id}`} className="text-foreground hover:text-primary/80 font-medium">{item.title}</Link></Td>
                    <Td><NeutralBadge value={item.status} /></Td>
                    <Td><RiskBadge value={item.severity} /></Td>
                    <Td><RiskBadge value={item.probability} /></Td>
                    <Td>{item.risk_category}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableCard>
        </div>
      )}

      {activeTab === 'changes' && (
        <div className="space-y-4">
          <SectionToolbar countLabel={`${changeRequests?.length ?? 0} change request${(changeRequests?.length ?? 0) !== 1 ? 's' : ''}`} actionLabel="New Change" onAction={() => navigate(`/projects/${prefix}/docs/new?type=CHG`)} />
          <TableCard emptyTitle="No Change Requests" emptyText="Capture requested changes and impact assessments here.">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <Th>ID</Th>
                  <Th>Title</Th>
                  <Th>Status</Th>
                  <Th>Priority</Th>
                  <Th>Type</Th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {(changeRequests ?? []).map((item) => (
                  <tr key={item.id} className="hover:bg-accent/50">
                    <Td><Link to={`/projects/${prefix}/docs/${item.change_id}`} className="text-primary font-mono text-sm font-medium">{item.change_id}</Link></Td>
                    <Td><Link to={`/projects/${prefix}/docs/${item.change_id}`} className="text-foreground hover:text-primary/80 font-medium">{item.title}</Link></Td>
                    <Td><NeutralBadge value={item.status} /></Td>
                    <Td><PriorityBadge priority={item.priority} /></Td>
                    <Td>{item.change_type}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableCard>
        </div>
      )}

      {activeTab === 'documents' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">All documents across all types in this project</p>
            </div>
            <div className="flex items-center gap-2">
              <Link to={`/projects/${prefix}/docs`} className="inline-flex items-center px-4 py-2 border border-input rounded-md hover:bg-accent/50 text-sm font-medium">
                <BookOpen className="h-4 w-4 mr-2" />
                Open Full View
              </Link>
              <NewDocDropdown prefix={prefix || ''} />
            </div>
          </div>

          {!documents || documents.length === 0 ? (
            <EmptyCard title="No Documents" text="Create your first document to get started." icon={BookOpen} />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {documents.slice(0, 6).map((doc) => (
                <Link key={doc.id} to={`/projects/${prefix}/docs/${doc.doc_id || doc.id}`} className="block bg-card rounded-lg border border-border shadow-elegant hover:border-primary/20 hover:shadow-glow transition-all p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="font-semibold text-foreground">{doc.title}</h3>
                      <p className="text-xs text-muted-foreground mt-1">{doc.doc_type} · v{doc.version}</p>
                    </div>
                    <NeutralBadge value={doc.status} />
                  </div>
                  {doc.description && <p className="text-sm text-muted-foreground mt-3 line-clamp-3">{doc.description}</p>}
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'test-concepts' && (
        <div className="space-y-4">
          <SectionToolbar countLabel={`${testConcepts?.length ?? 0} test concept${(testConcepts?.length ?? 0) !== 1 ? 's' : ''}`} actionLabel="New Test Concept" onAction={() => navigate(`/projects/${prefix}/docs/new?type=TCO`)} />
          {!testConcepts || testConcepts.length === 0 ? (
            <EmptyCard title="No Test Concepts" text="Create your first test concept for this project." icon={Beaker} />
          ) : (
            <TableCard emptyTitle="" emptyText="">
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/50">
                  <tr>
                    <Th>Name</Th>
                    <Th>Linked Requirements</Th>
                    <Th>Coverage</Th>
                    <Th>Status</Th>
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {testConcepts.map((concept: TestConceptRecord) => (
                    <tr key={concept.id} className="hover:bg-accent/50">
                      <Td>
                        <div>
                          <Link to={`/projects/${prefix}/docs/${concept.concept_id}`} className="font-medium text-foreground hover:text-primary/80">{concept.name}</Link>
                          {concept.description && <div className="text-sm text-muted-foreground mt-1">{concept.description}</div>}
                        </div>
                      </Td>
                      <Td>{concept.linked_requirement_ids.length}</Td>
                      <Td><CoverageBar coverage={concept.coverage} /></Td>
                      <Td><NeutralBadge value={concept.status} /></Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableCard>
          )}
        </div>
      )}

      {activeTab === 'traceability' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <SummaryPanel label="Matrix Rows" value={matrix?.length ?? 0} />
            <SummaryPanel label="Covered" value={matrix?.filter((item) => item.coverage_status === 'Covered').length ?? 0} />
            <SummaryPanel label="Partial" value={matrix?.filter((item) => item.coverage_status === 'Partial').length ?? 0} />
            <SummaryPanel label="Uncovered" value={matrix?.filter((item) => item.coverage_status === 'Uncovered').length ?? 0} accent="text-red-600" />
          </div>

          <div className="bg-card rounded-lg border border-border shadow-elegant p-5">
            <div className="flex items-center justify-between gap-4 mb-4">
              <div>
                <h3 className="font-semibold text-foreground">Inline Traceability View</h3>
                <p className="text-sm text-muted-foreground mt-1">Coverage problems are visible here without leaving the project workspace.</p>
              </div>
              <Link to={`/projects/${prefix}/traceability`} className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 text-sm">
                <GitBranch className="h-4 w-4 mr-2" />
                Open Full Matrix
              </Link>
            </div>

            {uncoveredRequirements.length === 0 ? (
              <div className="text-sm text-muted-foreground">No uncovered or partial requirements right now.</div>
            ) : (
              <div className="space-y-3">
                {uncoveredRequirements.map((item) => (
                  <div key={item.requirement.id} className="flex items-center justify-between gap-4 p-3 rounded-lg border border-border bg-background/60">
                    <div>
                      <Link to={`/projects/${prefix}/docs/${item.requirement.req_id}`} className="font-medium text-foreground hover:text-primary/80">
                        {item.requirement.req_id} · {item.requirement.title}
                      </Link>
                      <div className="text-sm text-muted-foreground mt-1">{item.linked_test_cases.length} linked test case{item.linked_test_cases.length !== 1 ? 's' : ''}</div>
                    </div>
                    <CoverageStatusBadge status={item.coverage_status} />
                  </div>
                ))}
              </div>
            )}

            {gapReport && (
              <div className="mt-4 pt-4 border-t border-border text-sm text-muted-foreground">
                Coverage gaps: {gapReport.gaps.length} · Coverage: {gapReport.coverage_percent}%
              </div>
            )}
          </div>
        </div>
      )}

      {showCreateReq && (
        <Modal title="New Requirement" onClose={() => setShowCreateReq(false)}>
          <form onSubmit={handleCreateReq} className="space-y-4">
            <TextInput label="Title" value={reqForm.title} onChange={(value) => setReqForm({ ...reqForm, title: value })} required />
            <TextArea label="Description" value={reqForm.description} onChange={(value) => setReqForm({ ...reqForm, description: value })} rows={3} />
            <div className="grid grid-cols-3 gap-4">
              <SelectInput label="Priority" value={reqForm.priority} onChange={(value) => setReqForm({ ...reqForm, priority: value })} options={['Low', 'Medium', 'High', 'Critical']} />
              <SelectInput label="Type" value={reqForm.req_type} onChange={(value) => setReqForm({ ...reqForm, req_type: value })} options={['Functional', 'Non-Functional', 'Performance', 'Security', 'Usability']} />
              <SelectInput label="Origin" value={reqForm.req_origin} onChange={(value) => setReqForm({ ...reqForm, req_origin: value })} options={['Internal', 'Customer', 'Compliance', 'Regulatory', 'Legal', 'Business', 'Technical']} />
            </div>
            <ModalActions onClose={() => setShowCreateReq(false)} submitting={createReqMutation.isPending} />
          </form>
        </Modal>
      )}

      {showCreateTc && (
        <Modal title="New Test Case" onClose={() => setShowCreateTc(false)} maxWidth="max-w-4xl">
          <form onSubmit={handleCreateTc} className="space-y-4">
            <TextInput label="Title" value={tcForm.title} onChange={(value) => setTcForm({ ...tcForm, title: value })} required />
            <TextArea label="Description" value={tcForm.description} onChange={(value) => setTcForm({ ...tcForm, description: value })} rows={3} />
            <TextArea label="Preconditions" value={tcForm.preconditions} onChange={(value) => setTcForm({ ...tcForm, preconditions: value })} rows={2} />
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Test Steps</label>
              <TcsArteTable rows={tcRows} onChange={setTcRows} editable />
            </div>
            <ModalActions onClose={() => { setShowCreateTc(false); setTcRows(createDefaultTcRows()) }} submitting={createTcMutation.isPending} />
          </form>
        </Modal>
      )}

      {showCreateConcept && (
        <Modal title="New Test Concept" onClose={() => setShowCreateConcept(false)}>
          <form onSubmit={handleCreateConcept} className="space-y-4">
            <TextInput label="Name" value={conceptForm.name} onChange={(value) => setConceptForm({ ...conceptForm, name: value })} required />
            <TextArea label="Description" value={conceptForm.description} onChange={(value) => setConceptForm({ ...conceptForm, description: value })} rows={3} />
            <div className="grid grid-cols-2 gap-4">
              <SelectInput label="Status" value={conceptForm.status} onChange={(value) => setConceptForm({ ...conceptForm, status: value })} options={['Draft', 'Review', 'Approved']} />
              <TextInput label="Coverage" value={conceptForm.coverage} onChange={(value) => setConceptForm({ ...conceptForm, coverage: value })} />
            </div>
            <ModalActions onClose={() => setShowCreateConcept(false)} submitting={createConceptMutation.isPending} />
          </form>
        </Modal>
      )}

      {showCreateDesign && (
        <Modal title="New Design Item" onClose={() => setShowCreateDesign(false)}>
          <form onSubmit={handleCreateDesign} className="space-y-4">
            <TextInput label="Title" value={designForm.title} onChange={(value) => setDesignForm({ ...designForm, title: value })} required />
            <TextArea label="Description" value={designForm.description} onChange={(value) => setDesignForm({ ...designForm, description: value })} rows={3} />
            <div className="grid grid-cols-2 gap-4">
              <SelectInput label="Status" value={designForm.status} onChange={(value) => setDesignForm({ ...designForm, status: value })} options={['Draft', 'Review', 'Approved']} />
              <SelectInput label="Priority" value={designForm.priority} onChange={(value) => setDesignForm({ ...designForm, priority: value })} options={['Low', 'Medium', 'High', 'Critical']} />
              <SelectInput label="Design Type" value={designForm.design_type} onChange={(value) => setDesignForm({ ...designForm, design_type: value })} options={['Architecture', 'Interface', 'Component', 'Data']} />
              <TextInput label="Linked Requirement ID" value={designForm.linked_requirement_id} onChange={(value) => setDesignForm({ ...designForm, linked_requirement_id: value })} />
            </div>
            <ModalActions onClose={() => setShowCreateDesign(false)} submitting={createDesignMutation.isPending} />
          </form>
        </Modal>
      )}

      {showCreateRisk && (
        <Modal title="New Risk" onClose={() => setShowCreateRisk(false)}>
          <form onSubmit={handleCreateRisk} className="space-y-4">
            <TextInput label="Title" value={riskForm.title} onChange={(value) => setRiskForm({ ...riskForm, title: value })} required />
            <TextArea label="Description" value={riskForm.description} onChange={(value) => setRiskForm({ ...riskForm, description: value })} rows={3} />
            <TextArea label="Mitigation" value={riskForm.mitigation} onChange={(value) => setRiskForm({ ...riskForm, mitigation: value })} rows={2} />
            <div className="grid grid-cols-2 gap-4">
              <SelectInput label="Status" value={riskForm.status} onChange={(value) => setRiskForm({ ...riskForm, status: value })} options={['Open', 'Monitoring', 'Mitigated', 'Closed']} />
              <SelectInput label="Severity" value={riskForm.severity} onChange={(value) => setRiskForm({ ...riskForm, severity: value })} options={['Low', 'Medium', 'High', 'Critical']} />
              <SelectInput label="Probability" value={riskForm.probability} onChange={(value) => setRiskForm({ ...riskForm, probability: value })} options={['Low', 'Medium', 'High']} />
              <SelectInput label="Category" value={riskForm.risk_category} onChange={(value) => setRiskForm({ ...riskForm, risk_category: value })} options={['Technical', 'Business', 'Compliance', 'Schedule', 'Security']} />
            </div>
            <TextInput label="Linked Requirement ID" value={riskForm.linked_requirement_id} onChange={(value) => setRiskForm({ ...riskForm, linked_requirement_id: value })} />
            <ModalActions onClose={() => setShowCreateRisk(false)} submitting={createRiskMutation.isPending} />
          </form>
        </Modal>
      )}

      {showCreateChange && (
        <Modal title="New Change Request" onClose={() => setShowCreateChange(false)}>
          <form onSubmit={handleCreateChange} className="space-y-4">
            <TextInput label="Title" value={changeForm.title} onChange={(value) => setChangeForm({ ...changeForm, title: value })} required />
            <TextArea label="Description" value={changeForm.description} onChange={(value) => setChangeForm({ ...changeForm, description: value })} rows={3} />
            <TextArea label="Impact Assessment" value={changeForm.impact_assessment} onChange={(value) => setChangeForm({ ...changeForm, impact_assessment: value })} rows={2} />
            <TextArea label="Justification" value={changeForm.justification} onChange={(value) => setChangeForm({ ...changeForm, justification: value })} rows={2} />
            <div className="grid grid-cols-3 gap-4">
              <SelectInput label="Status" value={changeForm.status} onChange={(value) => setChangeForm({ ...changeForm, status: value })} options={['Submitted', 'Analysis', 'Approved', 'Implemented', 'Rejected']} />
              <SelectInput label="Priority" value={changeForm.priority} onChange={(value) => setChangeForm({ ...changeForm, priority: value })} options={['Low', 'Medium', 'High', 'Critical']} />
              <SelectInput label="Type" value={changeForm.change_type} onChange={(value) => setChangeForm({ ...changeForm, change_type: value })} options={['Enhancement', 'Bug Fix', 'Refactor', 'Compliance']} />
            </div>
            <ModalActions onClose={() => setShowCreateChange(false)} submitting={createChangeMutation.isPending} />
          </form>
        </Modal>
      )}

    </div>
  )
}

function NewDocDropdown({ prefix }: { prefix: string }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const types = [
    { code: 'REQ', label: 'Requirement' },
    { code: 'TC', label: 'Test Case' },
    { code: 'DES', label: 'Design' },
    { code: 'RSK', label: 'Risk' },
    { code: 'CHG', label: 'Change Request' },
    { code: 'TCO', label: 'Test Concept' },
    { code: 'DOC', label: 'Document' },
  ]

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm font-medium"
      >
        <Plus className="h-4 w-4 mr-2" />
        New Document
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-48 bg-card border border-border rounded-lg shadow-elegant overflow-hidden z-50">
          {types.map((t) => (
            <button
              key={t.code}
              onClick={() => { setOpen(false); navigate(`/projects/${prefix}/docs/new?type=${t.code}`) }}
              className="w-full text-left px-4 py-2.5 text-sm text-foreground hover:bg-accent transition-colors"
            >
              {t.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function SectionToolbar({ children, countLabel, actionLabel, onAction }: { children?: ReactNode; countLabel: string; actionLabel: string; onAction: () => void }) {
  return (
    <div className="flex justify-between items-center gap-4 flex-wrap">
      <div className="flex items-center gap-3">
        {children}
        <span className="text-sm text-muted-foreground">{countLabel}</span>
      </div>
      <button onClick={onAction} className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm">
        <Plus className="h-4 w-4 mr-2" />
        {actionLabel}
      </button>
    </div>
  )
}

function SummaryTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-card rounded-lg border border-border shadow-elegant p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-2xl font-bold text-foreground mt-2">{value}</div>
    </div>
  )
}

function SummaryPanel({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div className="bg-card rounded-lg border border-border shadow-elegant p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className={`text-2xl font-bold mt-2 ${accent || 'text-foreground'}`}>{value}</div>
    </div>
  )
}

function TableCard({ children, emptyTitle, emptyText }: { children: ReactNode; emptyTitle: string; emptyText: string }) {
  const childArray = Array.isArray(children) ? children : [children]
  const table = childArray.find(Boolean)
  return (
    <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
      {table || (
        <div className="p-12 text-center">
          <h3 className="text-lg font-medium text-foreground mb-2">{emptyTitle}</h3>
          <p className="text-muted-foreground">{emptyText}</p>
        </div>
      )}
    </div>
  )
}

function EmptyCard({ title, text, icon: Icon }: { title: string; text: string; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="bg-card rounded-lg shadow-elegant p-12 text-center">
      <Icon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
      <h3 className="text-lg font-medium text-foreground mb-2">{title}</h3>
      <p className="text-muted-foreground">{text}</p>
    </div>
  )
}

function LoadingCard() {
  return <div className="bg-card rounded-lg shadow-elegant p-6 text-center text-muted-foreground">Loading...</div>
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">{children}</th>
}

function Td({ children }: { children: React.ReactNode }) {
  return <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{children}</td>
}

function Modal({ children, title, onClose, maxWidth = 'max-w-md' }: { children: ReactNode; title: string; onClose: () => void; maxWidth?: string }) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className={`bg-card rounded-lg shadow-elegant w-full ${maxWidth} max-h-[90vh] overflow-y-auto`}>
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button onClick={onClose} className="text-sm text-muted-foreground hover:text-foreground">Close</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}

function ModalActions({ onClose, submitting = false }: { onClose: () => void; submitting?: boolean }) {
  return (
    <div className="pt-2 flex justify-end gap-3">
      <button type="button" onClick={onClose} className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50">Cancel</button>
      <button type="submit" disabled={submitting} className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50">{submitting ? 'Saving...' : 'Save'}</button>
    </div>
  )
}

function TextInput({ label, value, onChange, required = false }: { label: string; value: string; onChange: (value: string) => void; required?: boolean }) {
  return (
    <div>
      <label className="block text-sm font-medium text-foreground mb-1">{label}</label>
      <input required={required} value={value} onChange={(e) => onChange(e.target.value)} className="w-full px-3 py-2 bg-background border border-input rounded-md" />
    </div>
  )
}

function TextArea({ label, value, onChange, rows, required = false }: { label: string; value: string; onChange: (value: string) => void; rows: number; required?: boolean }) {
  return (
    <div>
      <label className="block text-sm font-medium text-foreground mb-1">{label}</label>
      <textarea required={required} value={value} onChange={(e) => onChange(e.target.value)} rows={rows} className="w-full px-3 py-2 bg-background border border-input rounded-md" />
    </div>
  )
}

function SelectInput({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[] }) {
  return (
    <div>
      <label className="block text-sm font-medium text-foreground mb-1">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="w-full px-3 py-2 bg-background border border-input rounded-md">
        {options.map((option) => <option key={option}>{option}</option>)}
      </select>
    </div>
  )
}

function ProjectStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Active: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Archived: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Draft: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  }
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || colors.Draft}`}>{status}</span>
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
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || colors.Draft}`}>{status}</span>
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    Low: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Medium: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    High: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
    Critical: 'bg-red-500/10 text-red-700 dark:text-red-400',
  }
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[priority] || colors.Medium}`}>{priority}</span>
}

function TcStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Draft: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Active: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Deprecated: 'bg-red-500/10 text-red-700 dark:text-red-400',
  }
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || colors.Draft}`}>{status}</span>
}

function NeutralBadge({ value }: { value: string }) {
  return <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{value}</span>
}

function CoverageStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Covered: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Partial: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Uncovered: 'bg-red-500/10 text-red-700 dark:text-red-400',
  }
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || colors.Partial}`}>{status}</span>
}

function RiskBadge({ value }: { value: string }) {
  const colors: Record<string, string> = {
    Low: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Medium: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    High: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
    Critical: 'bg-red-500/10 text-red-700 dark:text-red-400',
  }
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[value] || colors.Medium}`}>{value}</span>
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
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[origin] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>{origin}</span>
}
