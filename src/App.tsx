import { Routes, Route, Link } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import RequirementDetail from './pages/RequirementDetail'
import TestCaseDetail from './pages/TestCaseDetail'
import TraceabilityMatrix from './pages/TraceabilityMatrix'
import ImpactAnalysis from './pages/ImpactAnalysis'
import TestCampaigns from './pages/TestCampaigns'
import CampaignDetail from './pages/CampaignDetail'
import Reports from './pages/Reports'
import Baselines from './pages/Baselines'
import Documents from './pages/Documents'
import DocumentDetail from './pages/DocumentDetail'

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
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="projects" element={<Projects />} />
        <Route path="projects/:id" element={<ProjectDetail />} />
        <Route path="projects/:id/documents" element={<Documents />} />
        <Route path="projects/:id/campaigns" element={<TestCampaigns />} />
        <Route path="projects/:id/campaigns/:campaignId" element={<CampaignDetail />} />
        <Route path="requirements/:id" element={<RequirementDetail />} />
        <Route path="test-cases/:id" element={<TestCaseDetail />} />
        <Route path="documents/:id" element={<DocumentDetail />} />
        <Route path="traceability/:projectId" element={<TraceabilityMatrix />} />
        <Route path="impact-analysis/:requirementId" element={<ImpactAnalysis />} />
        <Route path="reports" element={<Reports />} />
        <Route path="baselines" element={<Baselines />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default App
