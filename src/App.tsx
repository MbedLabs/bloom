import { Routes, Route, Link, Navigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import RequirementDetail from './pages/RequirementDetail'
import TestCaseDetail from './pages/TestCaseDetail'
import TraceabilityMatrix from './pages/TraceabilityMatrix'
import ImpactAnalysis from './pages/ImpactAnalysis'
import TestCampaigns from './pages/TestCampaigns'
import CampaignDetail from './pages/CampaignDetail'
import SuiteDetail from './pages/SuiteDetail'
import Reports from './pages/Reports'
import Baselines from './pages/Baselines'
import Users from './pages/Users'
import Documents from './pages/Documents'
import DocumentDetail from './pages/DocumentDetail'
import ArtefactDetail from './pages/ArtefactDetail'
import Settings from './pages/Settings'
import ProjectParameters from './pages/ProjectParameters'
import DocCreate from './pages/DocCreate'
import ImportWizard from './pages/ImportWizard'
import { requirementsApi, testCasesApi, designsApi, risksApi, changesApi, testConceptsApi, documentsApi } from './api/client'

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

  const routeMap: Record<string, string> = {
    requirement: 'requirements',
    'test-case': 'test-cases',
    document: 'documents',
    design: 'designs',
    risk: 'risks',
    change: 'changes',
    'test-concept': 'test-concepts',
  }

  const { data } = useQuery({
    queryKey: [type, numId],
    queryFn: () => apiMap[type](numId) as unknown as Promise<Record<string, unknown>>,
    enabled: !!numId,
  })

  if (data && 'project_id' in (data as Record<string, unknown>)) {
    return <Navigate to={`/projects/${data.project_id}/${routeMap[type]}/${id}`} replace />
  }

  return (
    <div className="flex items-center justify-center h-64 animate-fade-in">
      <div className="text-muted-foreground">Redirecting...</div>
    </div>
  )
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
        <Route path="projects/:id" element={<ProjectDetail />} />
        <Route path="projects/:id/documents" element={<Documents />} />
        <Route path="projects/:id/parameters" element={<ProjectParameters />} />
        <Route path="projects/:id/campaigns" element={<TestCampaigns />} />
        <Route path="projects/:id/suites/:suiteId" element={<SuiteDetail />} />
        <Route path="projects/:id/campaigns/:campaignId" element={<CampaignDetail />} />

        {/* Immersive doc creation and editing */}
        <Route path="projects/:id/docs/new" element={<DocCreate />} />
        <Route path="projects/:id/docs/:docId/edit" element={<DocCreate editMode />} />

        {/* Project-scoped doc detail routes */}
        <Route path="projects/:id/requirements/:itemId" element={<RequirementDetail />} />
        <Route path="projects/:id/test-cases/:itemId" element={<TestCaseDetail />} />
        <Route path="projects/:id/documents/:docId" element={<DocumentDetail />} />
        <Route path="projects/:id/designs/:itemId" element={<ArtefactDetail kind="design" />} />
        <Route path="projects/:id/risks/:itemId" element={<ArtefactDetail kind="risk" />} />
        <Route path="projects/:id/changes/:itemId" element={<ArtefactDetail kind="change" />} />
        <Route path="projects/:id/test-concepts/:itemId" element={<ArtefactDetail kind="test-concept" />} />
        <Route path="projects/:id/import" element={<ImportWizard />} />
        <Route path="projects/:id/traceability" element={<TraceabilityMatrix />} />
        <Route path="projects/:id/impact-analysis/:requirementId" element={<ImpactAnalysis />} />
        <Route path="projects/:id/baselines" element={<Baselines />} />

        {/* Legacy global routes redirect to project-scoped */}
        <Route path="requirements/:id" element={<RedirectResolver type="requirement" />} />
        <Route path="test-cases/:id" element={<RedirectResolver type="test-case" />} />
        <Route path="documents/:id" element={<RedirectResolver type="document" />} />
        <Route path="designs/:id" element={<RedirectResolver type="design" />} />
        <Route path="risks/:id" element={<RedirectResolver type="risk" />} />
        <Route path="changes/:id" element={<RedirectResolver type="change" />} />
        <Route path="test-concepts/:id" element={<RedirectResolver type="test-concept" />} />
        <Route path="traceability/:projectId" element={<RedirectResolver type="requirement" />} />
        <Route path="impact-analysis/:requirementId" element={<RedirectResolver type="requirement" />} />

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
