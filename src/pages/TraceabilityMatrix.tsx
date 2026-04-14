import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { traceabilityApi, projectsApi } from '../api/client'
import { ArrowLeft, CheckCircle, AlertCircle, XCircle, ExternalLink, Shield } from 'lucide-react'

export default function TraceabilityMatrix() {
  const { projectId } = useParams<{ projectId: string }>()
  const projId = parseInt(projectId || '0')

  const { data: project } = useQuery({
    queryKey: ['project', projId],
    queryFn: () => projectsApi.get(projId),
    enabled: !!projId,
  })

  const { data: matrix, isLoading, error } = useQuery({
    queryKey: ['traceability', projId],
    queryFn: () => traceabilityApi.getMatrix(projId),
    enabled: !!projId,
  })

  const totalRequirements = matrix?.length || 0
  const covered = matrix?.filter(m => m.coverage_status === 'Covered').length || 0
  const partial = matrix?.filter(m => m.coverage_status === 'Partial').length || 0
  const uncovered = matrix?.filter(m => m.coverage_status === 'Uncovered').length || 0
  const coveragePercent = totalRequirements > 0
    ? Math.round(((covered + partial) / totalRequirements) * 100)
    : 0

  const totalTestCases = matrix?.reduce((sum, m) => sum + m.linked_test_cases.length, 0) || 0

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-gray-500">Loading...</div>
  }

  if (error || !matrix) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-red-900">Traceability Data Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-teal-600 hover:text-teal-700">
          ← Back to Projects
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${projId}`} className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Traceability Matrix</h2>
            <p className="text-gray-500">{project?.name || `Project #${projId}`}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <SummaryCard
          label="Requirements"
          value={totalRequirements}
          icon={Shield}
          color="text-teal-600"
        />
        <SummaryCard
          label="Test Cases"
          value={totalTestCases}
          icon={CheckCircle}
          color="text-emerald-600"
        />
        <SummaryCard
          label="Coverage"
          value={`${coveragePercent}%`}
          icon={Shield}
          color={coveragePercent >= 80 ? 'text-emerald-600' : coveragePercent >= 50 ? 'text-amber-600' : 'text-red-600'}
        />
        <SummaryCard
          label="Uncovered"
          value={uncovered}
          icon={XCircle}
          color={uncovered > 0 ? 'text-red-600' : 'text-emerald-600'}
        />
      </div>

      <div className="flex items-center space-x-6 text-sm">
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-emerald-500 mr-2" />
          <span className="text-gray-600">Covered: {covered}</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-amber-500 mr-2" />
          <span className="text-gray-600">Partial: {partial}</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-red-500 mr-2" />
          <span className="text-gray-600">Uncovered: {uncovered}</span>
        </div>
      </div>

      {matrix.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <Shield className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Requirements</h3>
          <p className="text-gray-500">Add requirements to this project to see traceability data.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Req ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Coverage</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Test Cases</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Test Runs</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {matrix.map((item) => (
                <tr key={item.requirement.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link
                      to={`/requirements/${item.requirement.id}`}
                      className="font-mono text-sm text-teal-600 hover:text-teal-700 font-medium"
                    >
                      {item.requirement.req_id}
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <Link to={`/requirements/${item.requirement.id}`} className="text-gray-900 hover:text-teal-600">
                      {item.requirement.title}
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <PriorityBadge priority={item.requirement.priority} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <RequirementStatusBadge status={item.requirement.status} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <CoverageBadge status={item.coverage_status} />
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {item.linked_test_cases.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {item.linked_test_cases.map((tc) => (
                          <Link
                            key={tc.id}
                            to={`/test-cases/${tc.id}`}
                            className="inline-flex items-center px-2 py-0.5 bg-teal-50 text-teal-700 rounded text-xs font-mono hover:bg-teal-100"
                          >
                            {tc.tc_id}
                          </Link>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {item.linked_test_runs.length > 0 ? (
                      <div className="space-y-1">
                        {item.linked_test_runs.map((tr) => (
                          <div key={tr.id} className="flex items-center">
                            {tr.teststation_url ? (
                              <a
                                href={tr.teststation_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-teal-600 hover:text-teal-700 inline-flex items-center"
                              >
                                <ExternalLink className="h-3 w-3 mr-1" />
                                {tr.test_run_name || `#${tr.test_run_id}`}
                              </a>
                            ) : (
                              <span className="text-gray-500">{tr.test_run_name || `#${tr.test_run_id}`}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function SummaryCard({ label, value, icon: Icon, color }: {
  label: string
  value: number | string
  icon: React.ComponentType<{ className?: string }>
  color: string
}) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
        <Icon className={`h-8 w-8 ${color}`} />
      </div>
    </div>
  )
}

function CoverageBadge({ status }: { status: string }) {
  const config: Record<string, { colors: string; icon: React.ComponentType<{ className?: string }> }> = {
    Covered: { colors: 'bg-emerald-100 text-emerald-800', icon: CheckCircle },
    Partial: { colors: 'bg-amber-100 text-amber-800', icon: AlertCircle },
    Uncovered: { colors: 'bg-red-100 text-red-800', icon: XCircle },
  }
  const cfg = config[status] || config.Uncovered
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${cfg.colors}`}>
      <Icon className="h-3 w-3 mr-1" />
      {status}
    </span>
  )
}

function RequirementStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Draft: 'bg-gray-100 text-gray-800',
    Review: 'bg-amber-100 text-amber-800',
    Approved: 'bg-blue-100 text-blue-800',
    Implemented: 'bg-teal-100 text-teal-800',
    Verified: 'bg-emerald-100 text-emerald-800',
    Rejected: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
      {status}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    Low: 'bg-gray-100 text-gray-800',
    Medium: 'bg-blue-100 text-blue-800',
    High: 'bg-orange-100 text-orange-800',
    Critical: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[priority] || 'bg-gray-100 text-gray-800'}`}>
      {priority}
    </span>
  )
}
