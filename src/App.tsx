import { Routes, Route, Link, Navigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import TraceabilityMatrix from './pages/TraceabilityMatrix'
import ImpactAnalysis from './pages/ImpactAnalysis'
import TestCampaigns from './pages/TestCampaigns'
import CampaignDetail from './pages/CampaignDetail'
import SuiteDetail from './pages/SuiteDetail'
import Reports from './pages/Reports'
import Baselines from './pages/Baselines'
import Users from './pages/Users'
import Documents from './pages/Documents'
import Settings from './pages/Settings'
import ProjectParameters from './pages/ProjectParameters'
import DocCreate from './pages/DocCreate'
import ImportWizard from './pages/ImportWizard'
import UnifiedDocDetail from './pages/UnifiedDocDetail'
import { requirementsApi, testCasesApi, designsApi, risksApi, changesApi, testConceptsApi, documentsApi, projectsApi } from './api/client'

function RedirectResolver({ type }: { type: 'requirement' | 'test-case' | 'document' | 'design' | 'risk' | 'change' | 'test-concept' }) {
  const { id } = useParams<{ id: string }>()
  const numId = Number(id)

  const apiMap = {
    requirement: requirementsApi.get,
    'test-case': testCasesApi.get,
    document: documentsApi.get,
    design: designsApi.get,
    risk: risksApi.get,
    change: changesApi.get,
    'test-concept': testConceptsApi.get,
  }

  const docIdFieldMap: Record<string, string> = {
    requirement: 'req_id',
    'test-case': 'tc_id',
    document: 'doc_id',
    design: 'design_id',
    risk: 'risk_id',
    change: 'change_id',
    'test-concept': 'concept_id',
  }

  const { data } = useQuery({
    queryKey: [type, numId],
    queryFn: () => apiMap[type](numId) as unknown as Promise<Record<string, unknown>>,
    enabled: !!numId,
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
    enabled: !!data,
  })

  if (data && projects && 'project_id' in data) {
    const project = projects.find(p => p.id === Number(data.project_id))
    if (project) {
      const docId = data[docIdFieldMap[type]] as string
      return <Navigate to={`/projects/${project.prefix}/docs/${docId}`} replace />
    }
  }

  return (
    <div className="flex items-center justify-center h-64 animate-fade-in">
      <div className="text-muted-foreground">Redirecting...</div>
    </div>
  )
}

function TraceabilityRedirect() {
  const { projectId } = useParams<{ projectId: string }>()
  const numId = Number(projectId)

  const { data: project } = useQuery({
    queryKey: ['project', numId],
    queryFn: () => projectsApi.get(numId),
    enabled: !!numId,
  })

  if (project) {
    return <Navigate to={`/projects/${project.prefix}/traceability`} replace />
  }

  return <div className="flex items-center justify-center h-64"><div className="text-muted-foreground">Redirecting...</div></div>
}

function ImpactRedirect() {
  const { requirementId } = useParams<{ requirementId: string }>()
  const numId = Number(requirementId)

  const { data: req } = useQuery({
    queryKey: ['requirement', numId],
    queryFn: () => requirementsApi.get(numId),
    enabled: !!numId,
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
    enabled: !!req,
  })

  if (req && projects) {
    const project = projects.find(p => p.id === req.project_id)
    if (project) {
      return <Navigate to={`/projects/${project.prefix}/impact-analysis/${req.req_id}`} replace />
    }
  }

  return <div className="flex items-center justify-center h-64"><div className="text-muted-foreground">Redirecting...</div></div>
}

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-64 animate-fade-in">
      <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mb-5">
        <span className="text-3xl font-bold text-primary/40">404</span>
      </div>
      <h2 className="text-xl font-bold text-foreground mb-2">Page Not Found</h2>
      <p className="text-sm text-muted-foreground mb-4">The page you are looking for does not exist.</p>
      <Link to="/" className="text-sm font-medium text-primary hover:text-primary/80 transition-colors">
        &larr; Back to Dashboard
      </Link>
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="projects" element={<Projects />} />
        <Route path="projects/:prefix" element={<ProjectDetail />} />
        <Route path="projects/:prefix/docs" element={<Documents />} />
        <Route path="projects/:prefix/docs/new" element={<DocCreate />} />
        <Route path="projects/:prefix/docs/:docId/edit" element={<DocCreate editMode />} />
        <Route path="projects/:prefix/docs/:docId" element={<UnifiedDocDetail />} />
        <Route path="projects/:prefix/parameters" element={<ProjectParameters />} />
        <Route path="projects/:prefix/campaigns" element={<TestCampaigns />} />
        <Route path="projects/:prefix/suites/:suiteId" element={<SuiteDetail />} />
        <Route path="projects/:prefix/campaigns/:campaignId" element={<CampaignDetail />} />
        <Route path="projects/:prefix/traceability" element={<TraceabilityMatrix />} />
        <Route path="projects/:prefix/impact-analysis/:requirementId" element={<ImpactAnalysis />} />
        <Route path="projects/:prefix/baselines" element={<Baselines />} />
        <Route path="projects/:prefix/import" element={<ImportWizard />} />

        {/* Legacy global routes redirect to project-scoped Polarion URLs */}
        <Route path="requirements/:id" element={<RedirectResolver type="requirement" />} />
        <Route path="test-cases/:id" element={<RedirectResolver type="test-case" />} />
        <Route path="documents/:id" element={<RedirectResolver type="document" />} />
        <Route path="designs/:id" element={<RedirectResolver type="design" />} />
        <Route path="risks/:id" element={<RedirectResolver type="risk" />} />
        <Route path="changes/:id" element={<RedirectResolver type="change" />} />
        <Route path="test-concepts/:id" element={<RedirectResolver type="test-concept" />} />
        <Route path="traceability/:projectId" element={<TraceabilityRedirect />} />
        <Route path="impact-analysis/:requirementId" element={<ImpactRedirect />} />

        {/* Legacy numeric project routes redirect */}
        <Route path="projects/:prefix/requirements/:itemId" element={<UnifiedDocDetail />} />
        <Route path="projects/:prefix/test-cases/:itemId" element={<UnifiedDocDetail />} />
        <Route path="projects/:prefix/documents/:docId" element={<UnifiedDocDetail />} />
        <Route path="projects/:prefix/designs/:itemId" element={<UnifiedDocDetail />} />
        <Route path="projects/:prefix/risks/:itemId" element={<UnifiedDocDetail />} />
        <Route path="projects/:prefix/changes/:itemId" element={<UnifiedDocDetail />} />
        <Route path="projects/:prefix/test-concepts/:itemId" element={<UnifiedDocDetail />} />

        <Route path="reports" element={<Reports />} />
        <Route path="baselines" element={<Baselines />} />
        <Route path="users" element={<Users />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default App
