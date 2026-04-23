import { Routes, Route, Link } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import AcceptInvite from './pages/AcceptInvite'
import Dashboard from './pages/Dashboard'
import ForgotPassword from './pages/ForgotPassword'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import TraceabilityMatrix from './pages/TraceabilityMatrix'
import ImpactAnalysis from './pages/ImpactAnalysis'
import TestCampaigns from './pages/TestCampaigns'
import CampaignDetail from './pages/CampaignDetail'
import ResetPassword from './pages/ResetPassword'
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
import VerifyEmail from './pages/VerifyEmail'

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
      <Route path="/accept-invite" element={<AcceptInvite />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="projects" element={<Projects />} />
        <Route path="projects/:prefix" element={<ProjectDetail />} />
        <Route path="projects/:prefix/docs" element={<Documents />} />
        <Route path="projects/:prefix/docs/new" element={<DocCreate />} />
        <Route path="projects/:prefix/docs/:kind/:docId/edit" element={<DocCreate editMode />} />
        <Route path="projects/:prefix/docs/:kind/:docId" element={<UnifiedDocDetail />} />
        <Route path="projects/:prefix/parameters" element={<ProjectParameters />} />
        <Route path="projects/:prefix/campaigns" element={<TestCampaigns />} />
        <Route path="projects/:prefix/suites/:suiteId" element={<SuiteDetail />} />
        <Route path="projects/:prefix/campaigns/:campaignId" element={<CampaignDetail />} />
        <Route path="projects/:prefix/traceability" element={<TraceabilityMatrix />} />
        <Route path="projects/:prefix/impact-analysis/:requirementId" element={<ImpactAnalysis />} />
        <Route path="projects/:prefix/baselines" element={<Baselines />} />
        <Route path="projects/:prefix/import" element={<ImportWizard />} />

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
