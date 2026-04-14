import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import RequirementDetail from './pages/RequirementDetail'
import TestCaseDetail from './pages/TestCaseDetail'
import TraceabilityMatrix from './pages/TraceabilityMatrix'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="projects" element={<Projects />} />
        <Route path="projects/:id" element={<ProjectDetail />} />
        <Route path="requirements/:id" element={<RequirementDetail />} />
        <Route path="test-cases/:id" element={<TestCaseDetail />} />
        <Route path="traceability/:projectId" element={<TraceabilityMatrix />} />
      </Route>
    </Routes>
  )
}

export default App
