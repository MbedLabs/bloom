import { lazy } from 'react'
import { Routes, Route, Link } from 'react-router'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Setup from './pages/Setup'
import ConfirmEmailChange from './pages/ConfirmEmailChange'
import ResetPassword from './pages/ResetPassword'
import ForgotPassword from './pages/ForgotPassword'
import VerifyEmail from './pages/VerifyEmail'
import AcceptInvite from './pages/AcceptInvite'
import ErrorBoundary from './components/ErrorBoundary'

// Route-level splitting. Everything below sits behind authentication and a deliberate
// navigation; the document screens drag in TipTap and ProseMirror, 19 packages that
// were previously downloaded and parsed on every visit, including the login screen.
/* v8 ignore start -- these thunks hold no logic, and React only invokes
   them when a lazy route actually renders, which renderToString never does.
   Their one real failure mode is a path that does not resolve, which
   src/test/lazy-routes-resolve.test.ts checks for every entry below. */
const ArtefactDetail = lazy(() => import('./pages/ArtefactDetail'))
const Baselines = lazy(() => import('./pages/Baselines'))
const CampaignDetail = lazy(() => import('./pages/CampaignDetail'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Defects = lazy(() => import('./pages/Defects'))
const DocCreate = lazy(() => import('./pages/DocCreate'))
const Documents = lazy(() => import('./pages/Documents'))
const ImpactAnalysis = lazy(() => import('./pages/ImpactAnalysis'))
const ImportWizard = lazy(() => import('./pages/ImportWizard'))
const ProjectDetail = lazy(() => import('./pages/ProjectDetail'))
const ProjectEdit = lazy(() => import('./pages/ProjectEdit'))
const ProjectParameters = lazy(() => import('./pages/ProjectParameters'))
const Projects = lazy(() => import('./pages/Projects'))
const Reports = lazy(() => import('./pages/Reports'))
const Settings = lazy(() => import('./pages/Settings'))
const SuiteDetail = lazy(() => import('./pages/SuiteDetail'))
const TestCampaigns = lazy(() => import('./pages/TestCampaigns'))
const TraceabilityMatrix = lazy(() => import('./pages/TraceabilityMatrix'))
const UnifiedDocDetail = lazy(() => import('./pages/UnifiedDocDetail'))
const Users = lazy(() => import('./pages/Users'))
/* v8 ignore stop */

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-64 animate-fade-in">
      <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/10 to-violet-500/10 flex items-center justify-center mb-5">
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
      <Route path="/setup" element={<Setup />} />
      <Route path="/login" element={<Login />} />
      <Route path="/accept-invite" element={<AcceptInvite />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/confirm-email-change" element={<ConfirmEmailChange />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="projects" element={<Projects />} />
        <Route path="projects/:prefix/edit" element={<ProjectEdit />} />
        <Route path="projects/:prefix" element={<ProjectDetail />} />
        <Route path="projects/:prefix/docs" element={<Documents />} />
        <Route path="projects/:prefix/docs/new" element={<DocCreate />} />
        <Route path="projects/:prefix/docs/:kind/:docId/edit" element={<DocCreate editMode />} />
        <Route path="projects/:prefix/docs/:kind/:docId" element={<ErrorBoundary><UnifiedDocDetail /></ErrorBoundary>} />
        <Route path="projects/:prefix/parameters" element={<ProjectParameters />} />
        <Route path="projects/:prefix/defects" element={<Defects />} />
        <Route path="projects/:prefix/defects/:itemId" element={<ArtefactDetail kind="defect" />} />
        <Route path="projects/:prefix/campaigns" element={<TestCampaigns />} />
        <Route path="projects/:prefix/suites/:suiteId" element={<SuiteDetail />} />
        <Route path="projects/:prefix/campaigns/:campaignId" element={<ErrorBoundary><CampaignDetail /></ErrorBoundary>} />
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
